from config import Config

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