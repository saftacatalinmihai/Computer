import LLM_client_ollama
import LLM_client_openrouter
from datetime import datetime
from utils import Config
import json
import pprint
import time

from openai.types.chat.chat_completion import ChatCompletionMessage

# Helper function to get current assistant code
def get_current_assistant_code():
    """Reads and returns the content of the current assistant.py file."""
    # __file__ is the path to the current script (assistant.py)
    file_path = __file__
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # In a real scenario, might want more robust error logging
        print(f"Critical Error: Could not read own source code at {file_path}. Error: {e}")
        return "# Error: Could not read assistant code. Self-update features will be impaired."

# Tool implementation function for self-code-update
def update_assistant_code(new_code: str) -> str:
    """
    Overwrites the current assistant.py file with the new_code.
    Returns a status message.
    """
    file_path = __file__ # Path to the current assistant.py file
    try:
        with open(file_path.replace(".py", "_v2.py"), 'w', encoding='utf-8') as f:
            f.write(new_code)
        return "Assistant code successfully updated. The application MUST be restarted for changes to take effect."
    except Exception as e:
        return f"Error updating assistant code: {e}. Please ensure the new code is valid Python and try again."

def system_prompt(conn):
    tools_system_prompts = ""
    # TOOL_MAPPING is now a function, call it to get the current mapping
    current_tool_mapping = TOOL_MAPPING(conn)
    for tool_name in current_tool_mapping.keys():
        tool_data = current_tool_mapping[tool_name]
        tools_system_prompts += tool_data['system_prompt']

    return {
        "role": "system",
        "content": f"""
You are a helpful AI assistant.
The current date and time are: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
You have access to tools that you can run to help you respond to the user's requests.
Description and instructions for each tool follow: \n
""" + tools_system_prompts
    }


def call_llm(conversation_history) -> ChatCompletionMessage:
    pprint.pp(conversation_history)
    start_time = time.time() # Record start time

    if (Config.USE_OPEN_ROUTER):
        # Pass the global 'tools' list which contains the schemas for the LLM
        response = LLM_client_openrouter.call_llm(conversation_history, tools)
    else:
        # To use Ollama client instead, comment the line above and uncomment the line below:
        response = LLM_client_ollama.call_llm(conversation_history, tools) # TODO make Ollama work with tools as well

    end_time = time.time() # Record end time
    duration = end_time - start_time
    print(f"LLM call duration: {duration:.2f} seconds") # Print duration
    return response


def get_tool_response(conn, tool_calls):
    tool_responses = []
    current_tool_mapping = TOOL_MAPPING(conn) # Get current mapping

    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        tool_args = {}
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except Exception: # Catch more general JSON parsing errors
            tool_args = tool_call.function.arguments # Fallback if not JSON

        if tool_name in current_tool_mapping:
            tool_function = current_tool_mapping[tool_name]['function']
            try:
                # Call the function with the arguments.
                # For run_sql(conn), tool_function is inner(sql_statements)
                # For update_assistant_code, tool_function is update_assistant_code(new_code)
                tool_result = tool_function(**tool_args)
            except Exception as e:
                tool_result = f"Error executing tool {tool_name}: {e}"
        else:
            tool_result = f"Error: Tool '{tool_name}' not found in current mapping."

        tool_responses.append( {
            "role": "tool",
            # "tool_call_id": tool_call.id, # Original was commented, keeping as is
            "name": tool_name,
            "content": str(tool_result), # Ensure content is always a string
        })
    return tool_responses


# returns all the SQL table schemas as CREATE TABLE statements
def get_schema(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema_statements = []

    for table_name_tuple in tables:
        name = table_name_tuple[0]
        if name == 'sqlite_sequence':
            continue

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?;", (name,))
        create_statement_tuple = cursor.fetchone()
        if create_statement_tuple:
            schema_statements.append(create_statement_tuple[0])
    return "\n".join(schema_statements)

# Run SQL statement using the provided connection object.
def run_sql(conn):
    def inner(sql_statements: str): # Type hint for clarity
        column_names = []
        rows = []
        # Ensure parse_sql gets a string, as expected
        parsed_sql_list = parse_sql(str(sql_statements))
        for sql_statement in parsed_sql_list:
            if not sql_statement.strip(): # Skip empty statements
                continue
            cursor = conn.cursor()
            print("RUNNING SQL:")
            print(sql_statement)
            cursor.execute(sql_statement)
            # Get column names from cursor.description
            if cursor.description:
                column_names = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
            else: # For statements like INSERT, UPDATE, DELETE that don't return rows
                column_names = []
                rows = []
            conn.commit()
            print("DONE")
        # Format result of the last executed statement, if it produced rows
        if column_names and rows:
             return format_run_sql_result_as_md([dict(zip(column_names, row)) for row in rows])
        elif rows: # e.g. SELECT statements that return rows but somehow no column names (should not happen with typical DBs)
             return format_run_sql_result_as_md(rows)
        else: # No rows returned or DDL/DML statement
             return "SQL statement(s) executed successfully. No data returned."
    return inner

def parse_sql(assistant_response: str):
    all_statements = []
    # Split by semicolon, but be mindful of semicolons within string literals if they become an issue
    statements = assistant_response.split(';')
    cleaned_statements = [stmt.strip() for stmt in statements if stmt.strip()]
    all_statements.extend(cleaned_statements)
    return all_statements


from tabulate import tabulate
def format_run_sql_result_as_md(sql_results):
    if sql_results and isinstance(sql_results, list) and isinstance(sql_results[0], dict):
        headers = list(sql_results[0].keys())
        values = [list(row.values()) for row in sql_results]
        return "```\n" + tabulate(values, headers=headers, tablefmt="orgtbl") + "\n```\n"
    elif sql_results: # If it's not a list of dicts, but still some result
        return "```\n" + str(sql_results) + "\n```\n"
    else:
        return "```\n-\n``` (No results or an empty set was returned)"

def TOOL_MAPPING(conn):
   # Fetch current code and escape braces for f-string interpolation
   # This ensures the prompt contains the most up-to-date code at the time of generation
   current_code_for_prompt = get_current_assistant_code()

   return {
       "sqlite_sql_run": {
           "function": run_sql(conn),
           "system_prompt": f"""
Tool: sqlite_sql_run
Description: Runs SQL against an SQLite database (local.db).
Instructions:
- You interact with a user who is not familiar with SQL.
- Generate SQL code based on user requests. Keep it simple and use only SQLite-compatible features.
- No multi-tenancy, user access control, complex data validation, or error handling beyond basic SQL.
- For relative time (e.g., "yesterday"), use SQLite's relative time functions.
- DO NOT insert sample or placeholder data. Only use data mentioned by the user.
- After any DDL (CREATE, ALTER, DROP) or DML (INSERT, UPDATE, DELETE) statement, append a `SELECT * FROM table_name;` query for the modified table to show its new state.
- Assume tables might contain data, but you don't know what it is. Your role is to generate SQL.
- For querying, aim for broad matches (e.g., case-insensitive search if appropriate for the user's request).
- Provide only the final, executable SQL code. No hypothetical examples.
- If the schema seems insufficient for the user's request, include `CREATE TABLE` statements first, then the necessary DML.
- The existing SQLite SQL Schema is: \n{get_schema(conn)}\n
""",
       },
       "self-code-update": {
           "function": update_assistant_code, # Pass the function directly
           "system_prompt": """
Tool: self-code-update
Description: Allows you to update your own underlying Python code (`assistant.py`).
Instructions:
- You can add new tools, modify existing ones, or change any part of your operational logic by rewriting this file.
- When you use this tool, you MUST provide the *entire, complete* new Python code for `assistant.py`.
- Your current code for `assistant.py` is:
```python""" +
current_code_for_prompt + """
```
- To use this tool:
  1. Analyze the user's request for changes or your own assessment of needed improvements.
  2. Carefully construct the complete new Python code for `assistant.py`. Ensure it's valid Python.
  3. Call the `self-code-update` tool, passing the new code as the `new_code` string parameter.
  4. CRITICAL: After a successful update, you MUST inform the user that the application needs to be restarted for the changes to take effect. This is a manual process they (or the system operator) must perform.
- Be extremely careful. Ensure the new code is functional and maintains necessary existing structures unless a change in structure is the specific goal. Bugs in the new code can render you inoperable until manually fixed.
""",
       }
   }

# This 'tools' list is for the LLM client, defining the schema of available functions.
tools = [
  {
    "type": "function",
    "function": {
      "name": "sqlite_sql_run",
      "description": "Runs one or more SQL statements against an SQLite database and returns the result of the last query.",
      "parameters": {
        "type": "object",
        "properties": {
          "sql_statements": {
            "type": "string",
            "description": "A single string containing one or more SQL statements separated by semicolons. Example: 'CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT); INSERT INTO users (name) VALUES (\\'Alice\\'); SELECT * FROM users;'"
          }
        },
        "required": ["sql_statements"]
      }
    }
  },
  {
    "type": "function",
    "function": {
        "name": "self-code-update",
        "description": "Updates the assistant's own Python code. The entire new code for assistant.py must be provided.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_code": {
                    "type": "string",
                    "description": "The complete new Python code for the assistant.py file."
                }
            },
            "required": ["new_code"]
        }
    }
  }
]
