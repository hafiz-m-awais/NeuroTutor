import json
import logging
import threading
import time
from google import genai
from openai import OpenAI
from config import Config
from modules.prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

QUOTA_ERROR = "⏳ Switching to backup AI..."
QUOTA_FINAL = "⏳ All AI providers are at limit. Please wait 1 minute and try again."
GENERAL_ERROR = "Something went wrong. Please try again."

class KeyRotator:
    def __init__(self):
        self._lock = threading.Lock()
        self._keys = []
        self._clients = []
        self._current = 0
        self._cooldowns = {}

    def initialize(self, keys):
        self._keys = keys
        self._clients = [genai.Client(api_key=k) for k in keys]
        self._cooldowns = {i: 0.0 for i in range(len(keys))}
        log.info(f"KeyRotator initialized with {len(keys)} Gemini keys")

    def get_client(self):
        with self._lock:
            now = time.time()
            total = len(self._clients)
            for _ in range(total):
                idx = self._current % total
                self._current = (self._current + 1) % total
                if now >= self._cooldowns.get(idx, 0.0):
                    return self._clients[idx], idx
            return None, -1

    def mark_quota_exceeded(self, idx):
        with self._lock:
            self._cooldowns[idx] = time.time() + 65.0
            log.warning(f"Gemini Key {idx + 1} quota exceeded — cooling down 65s")

    def all_on_cooldown(self):
        now = time.time()
        return all(now < self._cooldowns.get(i, 0.0) for i in range(len(self._clients)))

rotator = KeyRotator()
grok_client = None

def initialize_keys():
    keys = Config.load_keys()
    rotator.initialize(keys)

    global grok_client
    if Config.GROK_API_KEY:
        grok_client = OpenAI(
            api_key=Config.GROK_API_KEY,
            base_url="https://api.x.ai/v1"
        )
        log.info("Grok client initialized as fallback")
    else:
        log.warning("No Grok API key found — fallback disabled")

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

def stream_with_grok(prompt: str, max_tokens: int = 1024, temperature: float = 0.7):
    if not grok_client:
        yield f"data: {json.dumps({'text': QUOTA_FINAL})}\n\n"
        yield "data: [DONE]\n\n"
        return
    try:
        log.info("Falling back to Grok")
        stream = grok_client.chat.completions.create(
            model=Config.GROK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        log.error(f"Grok error: {e}")
        yield f"data: {json.dumps({'text': QUOTA_FINAL})}\n\n"
        yield "data: [DONE]\n\n"

def generate_with_grok(prompt: str, max_tokens: int = 1024):
    if not grok_client:
        return None, QUOTA_FINAL
    try:
        log.info("Quiz falling back to Grok")
        response = grok_client.chat.completions.create(
            model=Config.GROK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.5
        )
        content = response.choices[0].message.content
        if not content:
            return None, "Empty response from Grok API"
        raw = content.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        return json.loads(raw), None
    except Exception as e:
        log.error(f"Grok quiz error: {e}")
        return None, GENERAL_ERROR

def stream_response(prompt: str):
    max_attempts = len(Config.GEMINI_API_KEYS)
    for attempt in range(max_attempts):
        if rotator.all_on_cooldown():
            yield from stream_with_grok(prompt)
            return
        client, idx = rotator.get_client()
        if client is None:
            yield from stream_with_grok(prompt)
            return
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
            return
        except Exception as e:
            if is_quota_error(e):
                rotator.mark_quota_exceeded(idx)
                if attempt < max_attempts - 1:
                    continue
                yield from stream_with_grok(prompt)
            else:
                log.error(f"Stream error: {e}")
                yield f"data: {json.dumps({'text': GENERAL_ERROR})}\n\n"
                yield "data: [DONE]\n\n"
            return

def stream_debug(code: str):
    from modules.prompts import DEBUG_PROMPT
    prompt = f"{DEBUG_PROMPT}\n\nBroken code to debug:\n```python\n{code}\n```"
    max_attempts = len(Config.GEMINI_API_KEYS)
    for attempt in range(max_attempts):
        if rotator.all_on_cooldown():
            yield from stream_with_grok(prompt, max_tokens=1024, temperature=0.3)
            return
        client, idx = rotator.get_client()
        if client is None:
            yield from stream_with_grok(prompt, max_tokens=1024, temperature=0.3)
            return
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
            return
        except Exception as e:
            if is_quota_error(e):
                rotator.mark_quota_exceeded(idx)
                if attempt < max_attempts - 1:
                    continue
                yield from stream_with_grok(prompt, max_tokens=1024, temperature=0.3)
            else:
                log.error(f"Debug error: {e}")
                yield f"data: {json.dumps({'text': GENERAL_ERROR})}\n\n"
                yield "data: [DONE]\n\n"
            return

def generate_quiz(topic: str):
    from modules.prompts import QUIZ_PROMPT
    prompt = QUIZ_PROMPT.replace("{topic}", topic)
    max_attempts = len(Config.GEMINI_API_KEYS)
    for attempt in range(max_attempts):
        if rotator.all_on_cooldown():
            return generate_with_grok(prompt)
        client, idx = rotator.get_client()
        if client is None:
            return generate_with_grok(prompt)
        try:
            response = client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "max_output_tokens": 1024,
                    "temperature": 0.5,
                }
            )
            if not getattr(response, 'text', None):
                return None, "Empty response from API"
            raw = response.text.strip()
            raw = raw.replace('```json', '').replace('```', '').strip()
            return json.loads(raw), None
        except Exception as e:
            if is_quota_error(e):
                rotator.mark_quota_exceeded(idx)
                if attempt < max_attempts - 1:
                    continue
                return generate_with_grok(prompt)
            else:
                log.error(f"Quiz error: {e}")
                return None, GENERAL_ERROR
    return generate_with_grok(prompt)