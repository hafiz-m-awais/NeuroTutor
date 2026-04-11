import json
import logging
from google import genai
from config import Config
from modules.prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

client = genai.Client(api_key=Config.GEMINI_API_KEY)

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
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            yield f"data: {json.dumps({'text': 'API limit reached. Please wait a minute and try again.'})}\n\n"
        else:
            yield f"data: {json.dumps({'text': 'Something went wrong. Please try again.'})}\n\n"
        yield "data: [DONE]\n\n"