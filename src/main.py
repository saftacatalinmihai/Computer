import base64
import uuid
import json
from functools import wraps

import replit
import requests
from flask import Flask, Response, redirect, render_template, request
from replit import db
from utils.env_loader import load_env_variables

load_env_variables()

import assistant_loader
from bot_slack import start_slack_bot
from tools import sql_postgres
from utils import get_logger, Config, require_auth

# Initialize logger
logger = get_logger(__name__)

# Initialize Flask app
app = Flask('app')

# Start Slack bot if enabled
if Config.ENABLE_SLACK_BOT:
    logger.info("Starting Slack bot")
    start_slack_bot()
else:
    logger.info("Slack bot is disabled")


@app.route('/')
def hello_world():
  return render_template('index.html')


# Load assistant module (Version 3 - SQLite, Version 4 - Postgres)
assistant = assistant_loader.load_assistant_module("4")
logger.info(f"Loaded assistant module: {assistant.__name__ if assistant else 'None'}")


@app.route('/computer', methods=['POST'])
@require_auth
def computer():
  content = request.get_json(silent=True)

  if content is None:
    # Handle the case where the content is None
    return "Invalid JSON data", 400

  if 'req' not in content or 'conv_id' not in content:
    # Handle the missing keys
    return "Missing 'req' or 'conv_id' in the request", 400

  req = content['req']
  conv_id = content['conv_id']
  logger.debug(f"Received request: {json.dumps(content)}")
  
  conv_hist = db.get("conversation_" + conv_id)

  # Get database connection
  conn = sql_postgres.get_connection_from_env_credentials()

  if req.startswith("version"):
    global assistant
    version = req.split("version")[1].strip()
    assistant = assistant_loader.load_assistant_module(version)
    conv_hist = [assistant.system_prompt(conn)]
    logger.info(f"Switched to assistant version: {version}")
    return "Switched to version: " + version

  if assistant is None:
    return "Failed to load assistant module", 500

  if conv_hist is None:
    conv_hist = [assistant.system_prompt(conn)]
  else:
    conv_hist = replit.database.to_primitive(conv_hist)
    conv_hist = [replit.database.to_primitive(i) for i in conv_hist]
  
  logger.debug(f"Conversation history: {json.dumps(conv_hist)}")
  conv_hist.append({"role": "user", "content": req})

  assistant_response = assistant.call_llm(conversation_history=conv_hist)
  logger.info("Received assistant response")
  logger.debug(f"Assistant response details: {assistant_response}")

  response = ""
  if assistant_response.tool_calls is not None:
    logger.info(f"Assistant is using tools: {len(assistant_response.tool_calls)} tool call(s)")
    try:
      # 'assistant' is now the dynamically imported module
      tool_responses = assistant.get_tool_response(
          conn, assistant_response.tool_calls)
      for tool_response in tool_responses:
        logger.debug(f"Tool response: {tool_response['content']}")
        conv_hist.append(tool_response)
      conv_hist.append({
          "role":
          "user",
          "content":
          """Reformat the tool responses in a very short and mobile friendly way. Think about displaying it in a chat app - use newlines as needed. Don't use a tool for this,  just do it. And don't mention that you are reformatting. Just give the response."""
      })
      assistant_response = assistant.call_llm(conversation_history=conv_hist)
      logger.info("Received follow-up assistant response after tool use")
      logger.debug(f"Follow-up response details: {assistant_response}")
      response += assistant_response.content
      conv_hist.append({
          "role": "assistant",
          "content": assistant_response.content
      })

    except Exception as e:
      logger.error(f"An unexpected error occurred while using tool: {e}", exc_info=True)
  else:
    logger.info("No tool called by assistant")
    if assistant_response.content is not None:
      logger.debug(f"Assistant content: {assistant_response.content}")
      response += assistant_response.content
      conv_hist.append({
          "role": "assistant",
          "content": assistant_response.content
      })
    else:
      # Handle cases where there's no content and no tool call (might indicate an issue)
      logger.warning("Assistant did not provide content or request a tool")
      conv_hist.append({
          "role": "assistant",
          "content": ""
      })  # Add empty assistant message
      response += "Assistant did not provide content or request a tool."

  ###

  db.set("conversation_" + conv_id, conv_hist)
  return response


@app.route('/new_conversation', methods=['GET'])
@require_auth
def new_conversation():
  return str(uuid.uuid4())

if __name__ == "__main__":
    logger.info(f"Starting server on {Config.HOST}:{Config.PORT}")
    app.run(host=Config.HOST, port=Config.PORT)
