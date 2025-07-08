import logging
import os

# Configure logging levels based on environment
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def get_logger(name):
    """
    Get a configured logger instance for the specified module.
    
    Args:
        name: The name of the module (typically __name__)
        
    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been configured yet
    if not logger.handlers:
        # Set the log level based on environment variable or default to INFO
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(console_handler)
        
        # Optionally add file handler if LOG_FILE is specified
        log_file = os.environ.get("LOG_FILE")
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_handler)
    
    return logger