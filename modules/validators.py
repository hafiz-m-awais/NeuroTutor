import re
from config import Config

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

def validate_email(email: str) -> tuple[bool, str]:
    if not email or not email.strip():
        return False, "Email is required"
    if not _EMAIL_RE.match(email.strip()):
        return False, "Invalid email address"
    if len(email) > 254:
        return False, "Email address too long"
    return True, ""

def validate_password(password: str) -> tuple[bool, str]:
    if not password:
        return False, "Password is required"
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {Config.MIN_PASSWORD_LENGTH} characters"
    return True, ""

def validate_question(question: str) -> tuple[bool, str]:
    if not question:
        return False, "Question cannot be empty"
    if len(question) < Config.MIN_INPUT_LENGTH:
        return False, "Question is too short"
    if len(question) > Config.MAX_INPUT_LENGTH:
        return False, f"Question too long. Max {Config.MAX_INPUT_LENGTH} characters."
    return True, ""

def validate_request(data: dict) -> tuple[bool, str]:
    if not data:
        return False, "Invalid request"
    question = data.get('question', '').strip()
    return validate_question(question)