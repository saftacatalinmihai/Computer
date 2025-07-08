import os
import re
import subprocess
import sys
import resource # Moved from line 101
from functools import wraps

from .logging_utils import get_logger

logger = get_logger(__name__)

def sanitize_input(input_str):
    """
    Sanitize input strings to prevent injection attacks.
    
    Args:
        input_str: The input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        return str(input_str)
    
    # Remove any potentially dangerous characters or patterns
    # This is a basic implementation and should be expanded based on specific needs
    sanitized = re.sub(r'[;<>&|]', '', input_str)
    return sanitized

def validate_sql(sql_statement):
    """
    Validate SQL statements to prevent SQL injection.
    
    Args:
        sql_statement: The SQL statement to validate
        
    Returns:
        Tuple of (is_valid, reason)
    """
    # IMPORTANT: While this function provides a layer of defense, the primary and most robust
    # way to prevent SQL injection is to use parameterized queries (prepared statements)
    # for all database interactions, rather than concatenating user input directly into SQL strings.
    
    # Check for common SQL injection patterns
    dangerous_patterns = [
        r'--',                  # SQL comment
        r'/\*.*\*/',            # Multi-line comment
        r'\bDROP\b',             # Attempting to drop tables
        r'\bDELETE\b.*FROM',     # Attempting to delete data
        r'UNION.*SELECT',       # UNION-based injection
        r'SELECT.*INTO.*OUTFILE', # File write attempt
        r'EXEC.*xp_',           # SQL Server stored procedures
        r'OR\s+\d+=\d+',         # Common boolean-based injection (e.g., OR 1=1)
        r'OR\s+\d+=\s*\d+',      # More flexible boolean-based injection
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, sql_statement, re.IGNORECASE):
            return False, f"SQL statement contains potentially dangerous pattern: {pattern}"
    
    return True, "SQL statement appears valid"

def sandbox_python_execution(code):
    """
    Execute Python code in a restricted sandbox environment.
    
    Args:
        code: The Python code to execute
        
    Returns:
        The output of the code execution
    """
    # WARNING: While this sandbox aims to restrict code execution, it's important to
    # understand that no software-based sandbox is 100% foolproof. Malicious code
    # might still find ways to escape or cause unintended side effects.
    # For highly sensitive environments, consider more robust isolation mechanisms
    # like Docker containers, virtual machines, or dedicated sandboxing solutions.
    
    # List of forbidden modules and functions
    forbidden_imports = [
        'os', 'subprocess', 'sys', 'shutil', 'importlib',
        'pickle', 'marshal', 'builtins', 'ctypes', 'socket'
    ]
    
    # Check for forbidden imports
    for module in forbidden_imports:
        if re.search(rf'\b(import|from)\s+{module}\b', code):
            return f"Error: Importing module '{module}' is not allowed for security reasons"
    
    # Check for other dangerous patterns
    dangerous_patterns = [
        r'__import__\(',
        r'eval\(',
        r'exec\(',
        r'compile\(',
        r'open\(',
        r'file\(',
        r'globals\(',
        r'locals\(',
        r'getattr\(',
        r'setattr\(',
        r'delattr\(',
        r'\b__class__\b',
        r'\b__bases__\b',
        r'\b__subclasses__\b',
        r'\b__mro__\b', # Added to prevent method resolution order inspection
        r'\bmro\b',     # Added to prevent method resolution order inspection
        r'\b__globals__\b', # Added to prevent access to global namespace
        r'\b__builtins__\b',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            return f"Error: Code contains potentially dangerous pattern: {pattern}"
    
    # Set resource limits for the execution
    def limit_resources():
        # Set CPU time limit to 5 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        # Set memory limit to 100MB
        resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
    
    # Execute the code in a separate process with resource limits
    temp_name = None # Initialize temp_name
    try:
        # Create a temporary file with the code
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp:
            temp.write(code.encode())
            temp_name = temp.name
        
        # Run the code in a separate process with resource limits
        result = subprocess.run(
            [sys.executable, temp_name],
            capture_output=True,
            text=True,
            timeout=5,  # 5 second timeout
            # preexec_fn=limit_resources # TODO fix - this seems to not work yet.
        )
        
        if result.returncode != 0:
            return f"Error: {result.stderr}"
        
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (5 second limit)"
    except Exception as e:
        logger.error(f"Error in sandbox_python_execution: {e}")
        return f"Error: {str(e)}"
    finally:
        # Ensure the temporary file is always cleaned up
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)

def require_auth(func):
    """
    Decorator to require authentication for API endpoints.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    from flask import request, Response
    from .config import Config
    
    @wraps(func)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return func(*args, **kwargs)
    
    def check_auth(username, password):
        """Check if username/password combination is valid"""
        return (username == Config.AUTH_USERNAME and 
                password == Config.AUTH_PASSWORD)
    
    def authenticate():
        """Send a 401 response with authentication challenge"""
        return Response(
            'Authentication required\n'
            'Please provide valid credentials', 401,
            {'WWW-Authenticate': 'Basic realm="API Authentication Required"'})
    
    return decorated