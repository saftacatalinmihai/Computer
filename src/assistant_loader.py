import importlib
import ollama


def load_assistant_module(version):
    assistant_module_name = f"assistant_v{version}"

    try:
        assistant = importlib.import_module(assistant_module_name)
        print(f"Successfully loaded assistant module: {assistant_module_name}")
        return assistant
    except ImportError as e:
        print(
            f"Error: Could not import assistant module '{assistant_module_name}'."
        )
        print(
            f"Please ensure '{assistant_module_name}.py' exists in the same directory as main.py or in the Python path."
        )
        print(f"Details: {e}")
        return  # Exit the REPL function if the assistant module cannot be loaded
