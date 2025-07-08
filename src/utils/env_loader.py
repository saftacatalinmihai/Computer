import os
from dotenv import dotenv_values

def load_env_variables():
    """
    Loads environment variables from the .env file.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    
    
    if os.path.exists(env_path):
        config = dotenv_values(dotenv_path=env_path)
        for key, value in config.items():
            os.environ[key] = str(value) if value is not None else ''
        print(f"Loaded environment variables from {env_path}")
    else:
        print(f"Warning: .env file not found at {env_path}. Using existing environment variables.")

if __name__ == "__main__":
    load_env_variables()
    # Example of accessing a loaded variable
    # print(f"PORT: {os.getenv('PORT')}")