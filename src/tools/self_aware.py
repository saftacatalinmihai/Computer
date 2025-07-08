import os
import re
import json


# Helper function to get current assistant code
def get_current_assistant_code(file_path):
    """Reads and returns the content of the current assistant.py file."""
    # file_path = __file__
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(
            f"Critical Error: Could not read own source code at {file_path}. Error: {e}"
        )
        return "# Error: Could not read assistant code. Self-update features will be impaired."


# Tool implementation function for self-code-update
def update_assistant_code(current_file_path):

    def update(new_code: str) -> str:
        """
        Overwrites the assistant's code with new_code, saving it to a new file
        with an incremented version number in its name (e.g., assistant_v2.py becomes assistant_v3.py).
        Returns a status message.
        """
        # current_file_path = __file__
        current_file_name = os.path.basename(current_file_path)
        current_dir = os.path.dirname(current_file_path)

        file_name_match = re.search(
            r"(?P<base>assistant_v)(?P<version>\d+)(?P<ext>\.py)",
            current_file_name)

        if not file_name_match:
            return (
                f"Error: Could not parse version from filename '{current_file_name}'. "
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
            return (
                f"Assistant code successfully updated and saved to '{new_file_path}'. "
                "The application MUST be restarted for changes to take effect."
            )
        except Exception as e:
            return (
                f"Error writing updated assistant code to '{new_file_path}': {e}. "
                "Please ensure the new code is valid Python and try again.")

    return update


def add_tool(current_file_path):

    def inner(system_prompt, tool_schema, tool_code):
        print("Prompt: " + system_prompt)
        print("Schema: " + tool_schema)
        print("Code " + tool_code)

        tool_schema_dict = json.loads(tool_schema)

        # current_file_path = __file__
        current_file_name = os.path.basename(current_file_path)
        current_dir = os.path.dirname(current_file_path)

        file_name_match = re.search(
            r"(?P<base>assistant_v)(?P<version>\d+)(?P<ext>\.py)",
            current_file_name)

        if not file_name_match:
            return (
                f"Error: Could not parse version from filename '{current_file_name}'. "
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

        crt_code_f = open(current_file_path, 'r', encoding='utf-8')
        new_code = crt_code_f.read()

        # TODO write code to file, include tool file in crt file, use imported code as function target.
        new_code = new_code.replace(
            "#<TOOL_MAPPING>,", f"""#<TOOL_MAPPING>,
            "{tool_schema_dict["function"]["name"]}": {{
                "function": {tool_schema_dict["function"]["name"]}.{tool_schema_dict["function"]["name"]},
                "system_prompt": \"\"\"{system_prompt}\"\"\"
            }},
            """)
        new_code = new_code.replace("#<tool_schma>,",
                                    f"""#<tool_schma>,\n{tool_schema},""")
        new_tool_file_path = os.path.join(
            current_dir, "tools", tool_schema_dict["function"]["name"] + ".py")

        # new_code = new_code.replace("#<TOOL_IMPORT>", f"from tools import {tool_schema_dict["function"]["name"]}\n#<TOOL_IMPORT>")

        try:
            with open(new_file_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            with open(new_tool_file_path, 'w', encoding='utf-8') as f:
                f.write(tool_code.replace("{{", "{").replace("}}", "}"))
            return (
                f"Assistant code successfully updated and saved to '{new_file_path}'. "
                "The application MUST be restarted for changes to take effect."
            )
        except Exception as e:
            return (
                f"Error writing updated assistant code to '{new_file_path}': {e}. "
                "Please ensure the new code is valid Python and try again.")

    return inner
