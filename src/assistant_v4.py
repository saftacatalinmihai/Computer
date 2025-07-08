import json
import pprint
import time
from datetime import datetime

#<TOOL_IMPORT>
import LLM_client_ollama
import LLM_client_openrouter
from utils import Config
from tools import ascii_art_generator, eval, self_aware, sql_postgres


def system_prompt(conn):
    tools_system_prompts = ""
    current_tool_mapping = TOOL_MAPPING(conn)
    for tool_name in current_tool_mapping:
        tool_data = current_tool_mapping[tool_name]
        tools_system_prompts += tool_data['system_prompt']

    return {
        "role":
        "system",
        "content":
        f"""
You are a helpful AI assistant.
The current date and time are: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
You have access to tools that you can run to help you respond to the user's requests.
Description and instructions for each tool follow: \n
""" + tools_system_prompts
    }


def call_llm(conversation_history):
    pprint.pp(conversation_history)
    start_time = time.time()

    if (Config.USE_OPEN_ROUTER):
        response = LLM_client_openrouter.call_llm(conversation_history, TOOLS)
    else:
        response = LLM_client_ollama.call_llm(conversation_history, TOOLS)

    end_time = time.time()
    duration = end_time - start_time
    print(f"LLM Response: {response}")
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
                "tool_call_id":
                tool_call.id,  # Original was commented, keeping as is
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


def TOOL_MAPPING(conn):
    current_code_for_prompt = self_aware.get_current_assistant_code(__file__)

    return {
        #<TOOL_MAPPING>,
        "ascii_art_generator": {
            "function":
            ascii_art_generator.ascii_art_generator,
            "system_prompt":
            """Tool: ascii_art_generator
Description: This tool generates ASCII art graphs from SQL query data. It can take data retrieved from SQL queries and produce simple ASCII representations of that data.
Instructions:
- Use this tool to create ASCII art graphs from data returned by SQL queries.
- The input data should be in a format suitable for creating graphs (e.g., numerical values).
- The output will be a string formatted as ASCII art.
- Ensure that the generated ASCII art is visually understandable and properly represents the data.
"""
        },
        "postgres_sql_run": {
            "function":
            sql_postgres.run_sql(conn),
            "system_prompt":
            f"""
Tool: postgres_sql_run
Description: Runs SQL against an Postgres database.
Instructions:
- You interact with a user who is not familiar with SQL.
- Generate SQL code based on user requests. Keep it simple and use only Postgres-compatible features.
- No multi-tenancy, user access control, complex data validation, or error handling beyond basic SQL.
- For relative time (e.g., "yesterday"), use Postgres's relative time functions.
- DO NOT insert sample or placeholder data. Only use data mentioned by the user.
- After any DDL (CREATE, ALTER, DROP) or DML (INSERT, UPDATE, DELETE) statement, append a `SELECT * FROM table_name;` query for the modified table to show its new state.
- Assume tables might contain data, but you don't know what it is. Your role is to generate SQL.
- For querying, aim for broad matches (e.g., case-insensitive search if appropriate for the user's request).
- Always add LIMIT 10 to SELECT queries and sort by date/timestamp columns in descending order (most recent first) unless the user specifically requests otherwise.
- Provide only the final, executable SQL code. No hypothetical examples.
- If the schema seems insufficient for the user's request, include `CREATE TABLE` statements first, then the necessary DML.
- The existing Postgres SQL Schema is: \n{sql_postgres.get_schema(conn)}\n
""",
        },
        "self-code-update": {
            "function":
            self_aware.add_tool(__file__),
            "system_prompt":
            """
Tool: self-code-update
Description: Allows you to update your own underlying Python code by adding new tools. The updated code will be saved to a new file with an incremented version number (e.g., if current is assistant_v2.py, new will be assistant_v3.py).
Your current code in file """ + __file__ +
            """  (from the file this instance is running from) is:
```python""" + current_code_for_prompt + """
```
- To use this tool:
  1. Analyze the user's request for changes or your own assessment of needed improvements.
  2. Carefully construct the complete new Python code. Ensure it's valid Python.
  3. Call the `self-code-update` tool, passing the system_prompt, tool_schema and tool_code parameters.
- Be extremely careful. Ensure the new code is functional and maintains necessary existing structures unless a change in structure is the specific goal. Bugs in the new code can render you inoperable until manually fixed.
""",
        },
        "python_code_executor": {
            "function":
            eval.execute_python_code,
            "system_prompt":
            """
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
TOOLS = [
    #<tool_schma>,
    {
        "type": "function",
        "function": {
            "name": "ascii_art_generator",
            "description": "Generates ASCII art graphs from SQL query data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {
                        "type":
                        "string",
                        "description":
                        "String representation of SQL query data to be graphically represented in ASCII format."
                    }
                },
                "required": ["data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "postgres_sql_run",
            "description":
            "Runs one or more SQL statements against an Postgres database and returns the result of the last query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql_statements": {
                        "type":
                        "string",
                        "description":
                        "A single string containing one or more SQL statements separated by semicolons."
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
            "description":
            "Updates the assistant's own Python code. The entire new code must be provided. The updated code will be saved to a new file with an incremented version number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "system_prompt": {
                        "type":
                        "string",
                        "description":
                        "The system prompt to include in the context of an LLM that describes how to use this tool"
                    },
                    "tool_schema": {
                        "type":
                        "string",
                        "description":
                        "The function schema to include in the tools list that is passed to the LLM in context so it knows the function name, description and interface of the tool for how to call it. Include the full type description with type, function, function.name etc..."
                    },
                    "tool_code": {
                        "type":
                        "string",
                        "description":
                        "The function definition for handling the implementation of this tool. Think of this as creating a new file with only the new function in it. It can have include statements above the function defitinion. Don't include a main, or other example usage code. Just the function code."
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
            "description":
            "Executes a given Python code snippet and returns the output or error messages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type":
                        "string",
                        "description":
                        "A string containing the Python code to be executed."
                    }
                },
                "required": ["code"]
            }
        }
    }
]
