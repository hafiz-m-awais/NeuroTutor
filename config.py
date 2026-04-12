import os
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

class Config:
    APP_NAME = os.getenv('APP_NAME', 'AskAI Pakistan')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', "gemini-2.0-flash-lite")
    GROK_MODEL = os.getenv('GROK_MODEL', 'grok-beta')
    GROK_API_KEY = os.getenv('GROK_API_KEY')
    MAX_INPUT_LENGTH = 500
    MIN_INPUT_LENGTH = 3
    MAX_OUTPUT_TOKENS = 1024
    TEMPERATURE = 0.7
    MAX_HISTORY = 4
    RATE_LIMIT_PER_MINUTE = "15 per minute"
    RATE_LIMIT_PER_HOUR = "20 per hour"
    RATE_LIMIT_PER_DAY = "200 per day"
    GEMINI_API_KEYS = []

    @classmethod
    def load_keys(cls):
        keys = []
        for i in range(1, 11):
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key and key.strip():
                keys.append(key.strip())
                log.info(f"Loaded GEMINI_API_KEY_{i}")
        if not keys:
            single = os.getenv('GEMINI_API_KEY')
            if single and single.strip():
                keys.append(single.strip())
                log.info("Loaded GEMINI_API_KEY (single)")
        if not keys:
            raise ValueError("No Gemini API keys found.")
        cls.GEMINI_API_KEYS = keys
        log.info(f"Total Gemini keys loaded: {len(keys)}")
        return keys