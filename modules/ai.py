import json
import logging
from google import genai
from config import Config
from modules.prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

client = Config.client

QUOTA_ERROR = "Free API limit reached. Please wait 1 minute and try again."
GENERAL_ERROR = "Something went wrong. Please try again."

def is_quota_error(e):
    msg = str(e).lower()
    return any(x in msg for x in ["quota", "limit", "429", "resource exhausted", "rate"])

def build_prompt(question: str, history: list) -> str:
    parts = [SYSTEM_PROMPT, ""]
    if len(history) > 1:
        parts.append("Previous conversation:")
        for msg in history[:-1]:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            speaker = 'Student' if role == 'user' else 'Tutor'
            parts.append(f"{speaker}: {content}")
        parts.append("")
    parts.append(f"Student: {question}")
    parts.append("Tutor:")
    return "\n".join(parts)

def stream_response(prompt: str):
    try:
        response = client.models.generate_content_stream(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config={
                "max_output_tokens": Config.MAX_OUTPUT_TOKENS,
                "temperature": Config.TEMPERATURE,
            }
        )
        for chunk in response:
            chunk_text = getattr(chunk, 'text', None)
            if chunk_text:
                yield f"data: {json.dumps({'text': chunk_text})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        log.error(f"Streaming error: {e}")
        msg = QUOTA_ERROR if is_quota_error(e) else GENERAL_ERROR
        yield f"data: {json.dumps({'text': msg})}\n\n"
        yield "data: [DONE]\n\n"

def stream_debug(code: str):
    from modules.prompts import DEBUG_PROMPT
    prompt = f"{DEBUG_PROMPT}\n\nBroken code to debug:\n```python\n{code}\n```"
    try:
        response = client.models.generate_content_stream(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config={
                "max_output_tokens": 1024,
                "temperature": 0.3,
            }
        )
        for chunk in response:
            chunk_text = getattr(chunk, 'text', None)
            if chunk_text:
                yield f"data: {json.dumps({'text': chunk_text})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        log.error(f"Debug streaming error: {e}")
        msg = QUOTA_ERROR if is_quota_error(e) else GENERAL_ERROR
        yield f"data: {json.dumps({'text': msg})}\n\n"
        yield "data: [DONE]\n\n"

def generate_quiz(topic: str):
    from modules.prompts import QUIZ_PROMPT
    prompt = QUIZ_PROMPT.replace("{topic}", topic)
    try:
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config={
                "max_output_tokens": 1024,
                "temperature": 0.5,
            }
        )
        if not response.text:
            return None, "Empty response from API"
        raw = response.text.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        return json.loads(raw), None

    except Exception as e:
        log.error(f"Quiz error: {e}")
        msg = QUOTA_ERROR if is_quota_error(e) else GENERAL_ERROR
        return None, msg