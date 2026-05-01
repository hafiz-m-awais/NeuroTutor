import os
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

class Config:
    APP_NAME = os.getenv('APP_NAME', 'AskAI Pakistan')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', "gemini-2.0-flash-lite")
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    _raw_secret = os.getenv('SECRET_KEY')
    if not _raw_secret:
        import warnings
        warnings.warn(
            "SECRET_KEY env var not set — using a temporary random key. "
            "All sessions will be invalidated on restart. Set SECRET_KEY in production.",
            RuntimeWarning, stacklevel=2
        )
    SECRET_KEY = _raw_secret or os.urandom(32).hex()
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///neurotutor.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_INPUT_LENGTH = 3000
    MIN_INPUT_LENGTH = 3
    MIN_PASSWORD_LENGTH = 8
    MAX_OUTPUT_TOKENS = 1024
    TEMPERATURE = 0.7
    MAX_HISTORY = 4
    RATE_LIMIT_PER_MINUTE = "15 per minute"
    RATE_LIMIT_PER_HOUR = "200 per hour"
    RATE_LIMIT_PER_DAY = "500 per day"
    _extra_origins = [
        o.strip() for o in os.getenv('ALLOWED_ORIGINS', '').split(',') if o.strip()
    ]
    ALLOWED_ORIGINS = [
        'http://localhost:7860',
        'http://127.0.0.1:7860',
        'https://awaisriaz-neurotutor.hf.space',
    ] + _extra_origins
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