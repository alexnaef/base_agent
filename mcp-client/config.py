import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env", override=True)

TOOL_MODEL = os.getenv("OPENAI_TOOL_MODEL", "gpt-4.1-mini")
FINAL_MODEL = os.getenv("OPENAI_FINAL_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MAX_LOOPS = 25

def validate_api_key():
    if OPENAI_API_KEY:
        print("API key loaded")
        return True
    else:
        print("WARNING: No OPENAI_API_KEY found in environment variables")
        return False