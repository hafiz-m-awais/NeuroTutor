import os
import sys
from dotenv import load_dotenv
from google import genai as _genai

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    APP_NAME = os.getenv('APP_NAME', 'NeuroTutor')
    
    client = _genai.Client(api_key=GEMINI_API_KEY)
    
    # Input/Output Limits
    MAX_INPUT_LENGTH = 500
    MIN_INPUT_LENGTH = 3
    MAX_OUTPUT_TOKENS = 1024
    TEMPERATURE = 0.7
    MAX_HISTORY = 4
    
    # Rate Limiting Rules
    RATE_LIMIT_PER_MINUTE = "15 per minute"
    RATE_LIMIT_PER_HOUR = "20 per hour"
    RATE_LIMIT_PER_DAY = "100 per day"

    # Fail-Fast Configuration validation
    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            print("CRITICAL ERROR: GEMINI_API_KEY is not set in environment variables.", file=sys.stderr)
            sys.exit(1)

# Run validation when config is loaded
Config.validate()