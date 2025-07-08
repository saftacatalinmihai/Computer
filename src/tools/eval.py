import sys
import io
from utils import get_logger, Config, sandbox_python_execution

# Initialize logger
logger = get_logger(__name__)

def execute_python_code(code: str) -> str:
    """
    Executes the given Python code and returns the output or error.
    
    If ENABLE_CODE_EXECUTION is set to False in the configuration,
    this function will return a message indicating that code execution
    is disabled for security reasons.
    
    Args:
        code: The Python code to execute
        
    Returns:
        The output of the code execution or an error message
    """
    logger.info("Received request to execute Python code")
    logger.debug(f"Code to execute: {code}")
    
    # Check if code execution is enabled
    if not Config.ENABLE_CODE_EXECUTION:
        logger.warning("Code execution is disabled by configuration")
        return "Code execution is disabled for security reasons. Set ENABLE_CODE_EXECUTION=true to enable."
    
    # Use the sandbox for secure execution if enabled
    try:
        if hasattr(Config, 'SANDBOX_EXECUTION') and Config.SANDBOX_EXECUTION:
            logger.info("Using sandbox for code execution")
            result = sandbox_python_execution(code)
        else:
            # Legacy execution method with basic safety
            logger.info("Using legacy code execution method")
            output = io.StringIO()
            sys.stdout = output
            try:
                # Execute in an empty global namespace for some isolation
                exec(code, {})
                result = output.getvalue()
            except Exception as e:
                result = f"Error: {e}"
            finally:
                sys.stdout = sys.__stdout__  # Reset redirect
    except Exception as e:
        logger.error(f"Error during code execution: {e}", exc_info=True)
        result = f"Error during code execution: {str(e)}"
    
    logger.info("Code execution completed")
    logger.debug(f"Execution result: {result}")
    
    return result.strip()
