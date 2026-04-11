import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
    APP_NAME = os.getenv('APP_NAME', 'AskAI Pakistan')
    MAX_INPUT_LENGTH = 500
    MIN_INPUT_LENGTH = 3
    MAX_OUTPUT_TOKENS = 1024
    TEMPERATURE = 0.7
    MAX_HISTORY = 4
    RATE_LIMIT_PER_MINUTE = "15 per minute"
    RATE_LIMIT_PER_HOUR = "20 per hour"
    RATE_LIMIT_PER_DAY = "100 per day"