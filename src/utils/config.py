import os

class Config:
    """
    Configuration class to centralize access to environment variables and configuration settings.
    This helps avoid hardcoded credentials and makes the codebase more secure for open sourcing.
    """
    
    # Server configuration
    PORT = int(os.environ.get("PORT", 8080))
    HOST = os.environ.get("HOST", "0.0.0.0")
    
    # Authentication
    AUTH_USERNAME = os.environ.get("AUTH_USERNAME")
    AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD")
    
    # Database configuration
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
    POSTGRES_DB = os.environ.get("POSTGRES_DB")
    POSTGRES_USER = os.environ.get("POSTGRES_USER")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
    POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", 5432))
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    # API keys and tokens
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
    
    SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
    SPOTIFY_REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "https://computer.saftacatalin.repl.co/callback")
    
    # Ollama configuration
    OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b")
    
    # LLM configuration
    DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "openai/gpt-4o-mini")
    
    # Feature flags
    USE_OPEN_ROUTER =  os.environ.get("USE_OPEN_ROUTER", "true").lower() == "true"
    ENABLE_SLACK_BOT = os.environ.get("ENABLE_SLACK_BOT", "false").lower() == "true"
    ENABLE_CODE_EXECUTION = os.environ.get("ENABLE_CODE_EXECUTION", "false").lower() == "true"
    SANDBOX_EXECUTION = os.environ.get("SANDBOX_EXECUTION", "true").lower() == "true"
    
    @classmethod
    def validate_required_env_vars(cls, required_vars):
        """
        Validate that required environment variables are set.
        
        Args:
            required_vars: List of required environment variable names
            
        Returns:
            Tuple of (is_valid, missing_vars)
        """
        missing_vars = [var for var in required_vars if getattr(cls, var, None) is None]
        return len(missing_vars) == 0, missing_vars