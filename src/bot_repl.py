import sqlite3
import os
import readline
import atexit
import time
import json
import pprint
import argparse # For command-line arguments
import assistant_loader
from tools import sql

# Define history file path (specific to the REPL)
history_file = os.path.join(os.path.expanduser("~"), ".sql_assistant_history")

# Function to save history (specific to the REPL)
def save_history():
    try:
        readline.write_history_file(history_file)
    except Exception as e:
        print(f"Error saving history file: {e}")

# Register save_history to be called on program exit
atexit.register(save_history)

def repl():
    # --- Argument Parsing for Assistant Version ---
    parser = argparse.ArgumentParser(description="REPL for LLM Assistant CLI.")
    parser.add_argument(
        "--version",
        type=str,
        required=True,
        help="Version number of the assistant module to load (e.g., '2' for assistant_v2.py, '3' for assistant_v3.py)."
    )

    # In a typical script, args are parsed once. If repl() could be called multiple times
    # with different args, this would need to be handled differently (e.g., pass args to repl).
    # For this __main__ structure, parsing here is fine.
    cli_args = parser.parse_args()
    assistant = assistant_loader.load_assistant_module(cli_args.version)

    # Load history
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass # It's ok if the file doesn't exist yet
    except Exception as e:
        print(f"Error loading history file: {e}")

    # CLI version creates its own connection
    conn = None
    try:
        conn = sqlite3.connect("local.db")
        print("Database connection established.")
        print(sql.get_schema(conn)) # Pass connection to get_schema

        conversation_history = []
        conversation_history.append(assistant.system_prompt(conn))

        while True:
            try:
                user_input = input("You: ")

                if user_input.lower() in ['quit', 'exit']:
                    print("Assistant: Goodbye!")
                    break

                if user_input.startswith("version"):
                    version = user_input.split("version")[1].strip()
                    assistant = assistant_loader.load_assistant_module(version)
                    conversation_history = []
                    conversation_history.append(assistant.system_prompt(conn))
                    print(f"Switchet to version: {version}")
                    continue

                conversation_history.append({"role": "user", "content": user_input})

                # 'assistant' is now the dynamically imported module
                assistant_response = assistant.call_llm(conversation_history=conversation_history)

                print("Assistant Response")
                pprint.pp(assistant_response)

                if assistant_response.tool_calls is not None:
                    print(f"USING TOOL")
                    pprint.pp(assistant_response.tool_calls)
                    try:
                        # 'assistant' is now the dynamically imported module
                        tool_responses = assistant.get_tool_response(conn, assistant_response.tool_calls)
                        for tool_response in tool_responses:
                            print("Tool response: " + tool_response["content"])
                            conversation_history.append(tool_response)
                    except Exception as e:
                         print(f"An unexpected error occurred while using tool: {e}")
                else:
                    print("No tool called by assistant.")
                    if assistant_response.content is not None:
                        print(assistant_response.content)
                        conversation_history.append({"role": "assistant", "content": assistant_response.content})
                    else:
                        # Handle cases where there's no content and no tool call (might indicate an issue)
                        print("Assistant did not provide content or request a tool.")
                        conversation_history.append({"role": "assistant", "content": ""}) # Add empty assistant message

            except EOFError:
                print("\nAssistant: Exiting.")
                break
            except KeyboardInterrupt:
                print("\nAssistant: Interrupted. Exiting.")
                break
            except Exception as e:
                print(f"An unexpected error occurred in the main loop: {e}")
                # conversation_history.append({'role': 'system', 'content': f"Unexpected error: {e}"})
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    repl()
