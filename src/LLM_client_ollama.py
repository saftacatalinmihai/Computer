import time

import ollama

from utils import get_logger, Config

# Initialize logger
logger = get_logger(__name__)

# Get Ollama URL from config
ollama_host = Config.OLLAMA_HOST
logger.info(f"Using Ollama host: {ollama_host}")

# Get model from config
OLLAMA_MODEL_NAME = Config.OLLAMA_MODEL
logger.info(f"Using Ollama model: {OLLAMA_MODEL_NAME}")

def call_llm(conversation_history, tools, model_name=None):
    """
    Calls the Ollama API with the given conversation history using the ollama library.

    Args:
        conversation_history: A list of message dictionaries
        tools: List of tool definitions
        model_name: Optional model name override
        
    Returns:
        The assistant's response message
    """
    if model_name is None:
        model_name = OLLAMA_MODEL_NAME
    
    logger.info(f"Calling Ollama with {len(conversation_history)} messages and {len(tools)} tools")
    logger.debug(f"Using model: {model_name}")
    
    start_time = time.time()
    
    try:
        client = ollama.Client(host=ollama_host)

        response = client.chat(
            model=model_name,
            messages=conversation_history,
            tools=tools,
            # stream=False # Default behavior is False (non-streaming)
        )
        
        logger.debug(f"Ollama response: {response}")
        conversation_history.append(response.message.dict())

        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Ollama call completed in {duration:.2f} seconds")
        
        # Extract the assistant's reply from the response
        if hasattr(response, 'message'):
            return response.message
        else:
            error_msg = f"Error: Unexpected response format from Ollama API"
            logger.error(error_msg)
            return error_msg

    except ollama.ResponseError as e:
        error_msg = f"Error calling Ollama API: {e}. Please ensure Ollama is running and the model '{model_name}' is available."
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred while calling Ollama: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg
