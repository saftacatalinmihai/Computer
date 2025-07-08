import json

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import assistant_loader
from tools import sql_postgres
from utils import get_logger, Config

# Initialize logger
logger = get_logger(__name__)

# In-memory store for conversation histories
# Key: thread_ts (or parent message ts for new threads)
# Value: list of conversation messages
conversation_histories = {}

# Load assistant module
assistant = None
try:
    assistant = assistant_loader.load_assistant_module("4")
    logger.info(f"Loaded assistant module: {assistant.__name__ if assistant else 'None'}")
except Exception as e:
    logger.error(f"Failed to load assistant module: {e}", exc_info=True)


def process_slack_message(app, say, body, logger_in_handler, client):
    """
    Process incoming Slack messages and generate responses using the assistant.
    
    Args:
        app: The Slack app instance
        say: Function to send messages to Slack
        body: The event body from Slack
        logger_in_handler: Logger instance provided by Slack bolt
        client: Slack client instance
    """
    event = body["event"]
    
    # Use the provided logger or fall back to the module logger
    log = logger_in_handler if logger_in_handler else logger

    # Ignore messages from bots, including self
    if "bot_id" in event:
        log.info(f"Ignoring bot message from {event.get('bot_id')}")
        return

    user_id = event["user"]
    text = event["text"]
    channel_id = event["channel"]
    message_ts = event["ts"]

    thread_id = event.get("thread_ts", message_ts)
    reply_in_thread_ts = thread_id

    log.info(f"Received message from user {user_id} in channel {channel_id} (thread: {thread_id}): {text}")

    if text.startswith("version"):
        global assistant
        version = text.split("version")[1].strip()
        try:
            assistant = assistant_loader.load_assistant_module(version)
            log.info(f"Switched to assistant version: {version}")
            say(text=f"Switched to version: {version}", thread_ts=reply_in_thread_ts)
        except Exception as e:
            error_msg = f"Failed to load assistant version {version}: {e}"
            log.error(error_msg)
            say(text=error_msg, thread_ts=reply_in_thread_ts)
        return

    conn = None
    try:
        conn = sql_postgres.get_connection_from_env_credentials()
        log.info("Database connection established")

        conversation_history = conversation_histories.get(thread_id, [])

        if not conversation_history:
            if assistant is None:
                error_msg = "Assistant module not loaded"
                if logger_in_handler:
                    logger_in_handler.error(error_msg)
                else:
                    print(error_msg)
                say(text=error_msg, thread_ts=reply_in_thread_ts)
                return
                
            system_message = assistant.system_prompt(conn)
            conversation_history.append(system_message)
            log.info(f"New conversation started for thread {thread_id}")

        conversation_history.append({"role": "user", "content": text})

        if assistant is None:
            error_msg = "Assistant module not loaded"
            if logger_in_handler:
                logger_in_handler.error(error_msg)
            else:
                print(error_msg)
            say(text=error_msg, thread_ts=reply_in_thread_ts)
            return
            
        assistant_response = assistant.call_llm(
            conversation_history=conversation_history)
        log.info(f"Received assistant response for thread {thread_id}")
        log.debug(f"LLM Raw Response: {assistant_response}")

        # Handle tool calls or content
        if assistant_response.tool_calls is not None:
            log.info(f"Assistant is using tools: {len(assistant_response.tool_calls)} tool call(s)")
            say(text="I will run the following Tools:", thread_ts=reply_in_thread_ts)
            for tool_call in assistant_response.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                say(text=f"Tool: {tool_name}\nArguments: {tool_args}",
                    thread_ts=reply_in_thread_ts)

            if assistant is None:
                error_msg = "Assistant module not loaded"
                if logger_in_handler:
                    logger_in_handler.error(error_msg)
                else:
                    print(error_msg)
                say(text=error_msg, thread_ts=reply_in_thread_ts)
                return
                
            tool_responses = assistant.get_tool_response(
                conn, assistant_response.tool_calls)
            for tool_response in tool_responses:
                log.debug(f"Tool response: {tool_response['content']}")
                tool_response_content = tool_response["content"]
                say(text=f"Result: {tool_response_content}", thread_ts=reply_in_thread_ts)
                conversation_history.append(tool_response)

        else:
            log.info("No tool called by assistant")
            say(text=assistant_response.content, thread_ts=reply_in_thread_ts)
            conversation_history.append({
                "role": "assistant",
                "content": assistant_response.content
            })

        conversation_histories[thread_id] = conversation_history
        log.info(f"Conversation history for thread {thread_id} updated. Length: {len(conversation_history)}")

    except Exception as e:
        log.error(f"Error in process_slack_message for thread {thread_id}: {e}", exc_info=True)

        try:
            error_message = f"I'm sorry, I encountered an unexpected error while processing your request: {str(e)}"
            say(text=error_message, thread_ts=reply_in_thread_ts)
            
            # Record the error in conversation history
            if thread_id in conversation_histories and conversation_histories[thread_id]:
                conversation_histories[thread_id].append({
                    "role": "system",
                    "content": f"Unhandled error: {str(e)}"
                })
            elif thread_id not in conversation_histories:
                conversation_histories[thread_id] = [{
                    "role": "system",
                    "content": f"Unhandled error before history init: {str(e)}"
                }]

        except Exception as say_e:
            log.error(f"Failed to send error message to Slack for thread {thread_id}: {say_e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            log.info("Database connection closed")


def start_slack_bot():
    """
    Start the Slack bot using Socket Mode.
    
    This function initializes the Slack bot with the provided tokens
    and sets up event handlers for app_mention and message events.
    """
    # Get tokens from config
    bot_token = Config.SLACK_BOT_TOKEN
    app_token = Config.SLACK_APP_TOKEN

    # Validate tokens
    if not bot_token:
        logger.error("SLACK_BOT_TOKEN environment variable not set")
        return
    if not app_token:
        logger.error("SLACK_APP_TOKEN environment variable not set")
        return

    logger.info("Initializing Slack bot")
    app = App(token=bot_token)

    def event_handler_wrapper(body, logger, client, say):
        """
        Wrapper function for handling Slack events.
        
        This function wraps the process_slack_message function with error handling
        and logging to ensure that any exceptions are properly caught and reported.
        
        Args:
            body: The event body from Slack
            logger: Logger instance provided by Slack bolt
            client: Slack client instance
            say: Function to send messages to Slack
        """
        try:
            # Pass the injected logger and say to process_slack_message
            process_slack_message(
                app=app,
                say=say,
                body=body,
                logger_in_handler=logger,
                client=client
            )
        except Exception as e:
            # Log the error with the injected logger
            logger.error(f"Critical error in event_handler_wrapper: {e}", exc_info=True)
            
            try:
                # Attempt to notify the user in the thread
                event = body.get("event", {})
                reply_ts = event.get("thread_ts", event.get("ts"))
                if reply_ts:
                    say(
                        text=f"A critical error occurred while processing your message. Our team has been notified.",
                        thread_ts=reply_ts
                    )
            except Exception as nested_e:
                logger.error(f"Failed to send critical error notification: {nested_e}", exc_info=True)

    app.event("app_mention")(event_handler_wrapper)
    app.event("message")(event_handler_wrapper)

    handler = SocketModeHandler(app, app_token)
    logger.info("Slack bot is starting in Socket Mode...")
    
    try:
        handler.start()
        logger.info("Slack bot started successfully")
    except Exception as e:
        logger.error(f"Failed to start Slack bot: {e}", exc_info=True)


if __name__ == "__main__":
    start_slack_bot()
