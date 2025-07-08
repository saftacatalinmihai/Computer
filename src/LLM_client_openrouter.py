import json
import time

import requests
from openai import OpenAI

from utils import get_logger, Config

# Initialize logger
logger = get_logger(__name__)

# Get API key from config
api_key = Config.OPENROUTER_API_KEY
if not api_key:
    logger.error("OPENROUTER_API_KEY is not set in environment variables")

# Initialize OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# Get model from config or use default
MODEL = Config.DEFAULT_LLM_MODEL
logger.info(f"Using LLM model: {MODEL}")


def call_llm(conversation_history, tools):
    """
    Call the LLM API with the given conversation history and tools.
    
    Args:
        conversation_history: List of message dictionaries
        tools: List of tool definitions
        
    Returns:
        The LLM's response message
    """
    logger.info(f"Calling LLM with {len(conversation_history)} messages and {len(tools)} tools")
    
    start_time = time.time()
    
    request = {
        "model": MODEL,
        "tools": tools,
        "messages": conversation_history
    }
    
    try:
        completion = client.chat.completions.create(**request)
        conversation_history.append(completion.choices[0].message.dict())
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"LLM call completed in {duration:.2f} seconds")
        
        return completion.choices[0].message
    except Exception as e:
        logger.error(f"Error calling LLM: {e}", exc_info=True)
        raise


def call_llm_stream(conversation_history):
    """
    Call the LLM API with streaming enabled.
    
    Args:
        conversation_history: List of message dictionaries
        
    Returns:
        The full response as a string
    """
    logger.info(f"Calling LLM with streaming for {len(conversation_history)} messages")
    
    start_time = time.time()
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": conversation_history,
        "stream": True
    }
    
    buffer = ""
    full_response = ""
    
    try:
        with requests.post(url, headers=headers, json=payload, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024, decode_unicode=True):
                buffer += chunk
                while True:
                    try:
                        # Find the next complete SSE line
                        line_end = buffer.find('\n')
                        if line_end == -1:
                            break
                        line = buffer[:line_end].strip()
                        buffer = buffer[line_end + 1:]
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            try:
                                data_obj = json.loads(data)
                                content = data_obj["choices"][0]["delta"].get("content")
                                if content:
                                    logger.debug(f"Received content chunk: {content}")
                                    full_response += content
                            except json.JSONDecodeError:
                                pass
                    except Exception as e:
                        logger.error(f"Error processing stream chunk: {e}")
                        break
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"LLM streaming call completed in {duration:.2f} seconds")
        
        return full_response
    except Exception as e:
        logger.error(f"Error in streaming LLM call: {e}", exc_info=True)
        raise
