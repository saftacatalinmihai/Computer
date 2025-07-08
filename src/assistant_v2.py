import LLM_client_ollama
import LLM_client_openrouter
from datetime import datetime
import json
import pprint
import time
import sys
import io
import re
import os

from openai.types.chat.chat_completion_message import ChatCompletionMessage

# Helper function to get current assistant code
def get_current_assistant_code():
    """Reads and returns the content of the current assistant.py file."""
    file_path = __file__
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Critical Error: Could not read own source code at {file_path}. Error: {e}")
        return "# Error: Could not read assistant code. Self-update features will be impaired."

# Tool implementation function for self-code-update
def update_assistant_code(new_code: str) -> str:
    """
    Overwrites the assistant's code with new_code, saving it to a new file
    with an incremented version number in its name (e.g., assistant_v2.py becomes assistant_v3.py).
    Returns a status message.
    """
    current_file_path = __file__
    current_file_name = os.path.basename(current_file_path)
    current_dir = os.path.dirname(current_file_path)

    file_name_match = re.search(r"(?P<base>assistant_v)(?P<version>\d+)(?P<ext>\.py)", current_file_name)

    if not file_name_match:
        return (f"Error: Could not parse version from filename '{current_file_name}'. "
                "Expected format like 'assistant_vN.py'. Update aborted.")

    base_name_part = file_name_match.group("base")
    version_str = file_name_match.group("version")
    extension_part = file_name_match.group("ext")

    try:
        current_version = int(version_str)
        new_version = current_version + 1
        new_file_basename = f"{base_name_part}{new_version}{extension_part}"
        new_file_path = os.path.join(current_dir, new_file_basename)
    except ValueError:
        return f"Error: Could not convert version '{version_str}' to an integer. Update aborted."
    except Exception as e:
        return f"Error constructing new file path: {e}. Update aborted."

    try:
        with open(new_file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        return (f"Assistant code successfully updated and saved to '{new_file_path}'. "
                "The application MUST be restarted for changes to take effect.")
    except Exception as e:
        return (f"Error writing updated assistant code to '{new_file_path}': {e}. "
                "Please ensure the new code is valid Python and try again.")

def execute_python_code(code: str) -> str:
    """Executes the given Python code and returns the output or error."""
    # Capture the output of the execution
    print(f"Executing python code: {code}")
    output = io.StringIO()
    sys.stdout = output
    try:
        exec(code, {})
        result = output.getvalue()
    except Exception as e:
        result = f"Error: {e}"
    finally:
        sys.stdout = sys.__stdout__  # Reset redirect.

    print(f"Code result: {result}")
    return result.strip()

def system_prompt(conn):
    tools_system_prompts = ""
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
    start_time = time.time()

    if (True):
        response = LLM_client_openrouter.call_llm(conversation_history, tools)
    else:
        response = LLM_client_ollama.call_llm(conversation_history, tools)

    end_time = time.time()
    duration = end_time - start_time
    print(f"LLM call duration: {duration:.2f} seconds")
    return response

def get_tool_response(conn, tool_calls):
    tool_responses = []
    current_tool_mapping = TOOL_MAPPING(conn)

    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        tool_args = {}
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except Exception:
            tool_args = tool_call.function.arguments

        if tool_name in current_tool_mapping:
            tool_function = current_tool_mapping[tool_name]['function']
            try:
                tool_result = tool_function(**tool_args)
            except Exception as e:
                tool_result = f"Error executing tool {tool_name}: {e}"
        else:
            tool_result = f"Error: Tool '{tool_name}' not found in current mapping."

        if hasattr(tool_call, 'id'):
            tool_responses.append({
                "role": "tool",
                "tool_call_id": tool_call.id, # Original was commented, keeping as is
                "name": tool_name,
                "content": str(tool_result),
            })
        else:
            tool_responses.append({
                "role": "tool",
                "name": tool_name,
                "content": str(tool_result),
            })

    return tool_responses

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

def run_sql(conn):
    def inner(sql_statements: str):
        column_names = []
        rows = []
        parsed_sql_list = parse_sql(str(sql_statements))
        for sql_statement in parsed_sql_list:
            if not sql_statement.strip():
                continue
            cursor = conn.cursor()
            print("RUNNING SQL:")
            print(sql_statement)
            cursor.execute(sql_statement)
            if cursor.description:
                column_names = [description[0] for description in cursor.description]
                rows = cursor.fetchall()
            else:
                column_names = []
                rows = []
            conn.commit()
            print("DONE")
        if column_names and rows:
            return format_run_sql_result_as_md([dict(zip(column_names, row)) for row in rows])
        elif rows:
            return format_run_sql_result_as_md(rows)
        else:
            return "SQL statement(s) executed successfully. No data returned."
    return inner

def parse_sql(assistant_response: str):
    all_statements = []
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
           "function": update_assistant_code,
           "system_prompt": """
Tool: self-code-update
Description: Allows you to update your own underlying Python code. The updated code will be saved to a new file with an incremented version number (e.g., if current is assistant_v2.py, new will be assistant_v3.py).
Instructions:
- You can add new tools, modify existing ones, or change any part of your operational logic by rewriting this file.
- When you use this tool, you MUST provide the *entire, complete* new Python code for the assistant logic.
- Your current code (from the file this instance is running from) is:
```python""" + current_code_for_prompt + """
```
- To use this tool:
  1. Analyze the user's request for changes or your own assessment of needed improvements.
  2. Carefully construct the complete new Python code. Ensure it's valid Python.
  3. Call the `self-code-update` tool, passing the new code as the `new_code` string parameter.
  4. CRITICAL: After a successful update, you MUST inform the user that the application needs to be restarted (using the new version file) for the changes to take effect. This is a manual process they (or the system operator) must perform.
- Be extremely careful. Ensure the new code is functional and maintains necessary existing structures unless a change in structure is the specific goal. Bugs in the new code can render you inoperable until manually fixed.
""",
       },
       "python_code_executor": {
           "function": execute_python_code,
           "system_prompt": """
Tool: python_code_executor
Description: Executes a given Python code snippet and returns the output or any errors encountered during execution.
Use this for mathemathical computations or anything that requires exact responses which could be implemented as python code.
Instructions:
- Provide a valid Python code snippet as input.
- The output will include any results printed or error messages generated during execution.
- Always print the result of the computation that you want to output, don't just return it.
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
            "description": "A single string containing one or more SQL statements separated by semicolons."
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
        "description": "Updates the assistant's own Python code. The entire new code must be provided. The updated code will be saved to a new file with an incremented version number.",
        "parameters": {
            "type": "object",
            "properties": {
                "new_code": {
                    "type": "string",
                    "description": "The complete new Python code for the assistant."
                }
            },
            "required": ["new_code"]
        }
    }
  },
  {
    "type": "function",
    "function": {
        "name": "python_code_executor",
        "description": "Executes a given Python code snippet and returns the output or error messages.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "A string containing the Python code to be executed."
                }
            },
            "required": ["code"]
        }
    }
  }
]
