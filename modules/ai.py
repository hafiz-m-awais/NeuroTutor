import json
import logging
import threading
import time
from google import genai
from openai import OpenAI
from config import Config
from modules.prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

QUOTA_FINAL = "⏳ All AI providers are busy. Please wait 1 minute and try again."
GENERAL_ERROR = "Something went wrong. Please try again."

OPENROUTER_MODELS = [ 
    "qwen/qwen-2.5-72b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "deepseek/deepseek-chat:free",
    "microsoft/phi-3-medium-128k-instruct:free",
    "openchat/openchat-7b:free"
]

_or_index = 0
_or_lock = threading.Lock()

def get_openrouter_model():
    global _or_index
    with _or_lock:
        model = OPENROUTER_MODELS[_or_index % len(OPENROUTER_MODELS)]
        _or_index += 1
    log.info(f"OpenRouter model selected: {model}")
    return model

class KeyRotator:
    def __init__(self):
        self._lock = threading.Lock()
        self._clients = []
        self._current = 0
        self._cooldowns: dict = {}

    def initialize(self, keys):
        self._clients = [genai.Client(api_key=k) for k in keys]
        self._cooldowns = {i: 0 for i in range(len(keys))}
        log.info(f"Gemini: {len(keys)} keys loaded")

    def get_client(self):
        with self._lock:
            now = time.time()
            total = len(self._clients)
            for _ in range(total):
                idx = self._current % total
                self._current = (self._current + 1) % total
                if now >= self._cooldowns.get(idx, 0):
                    return self._clients[idx], idx
            return None, -1

    def mark_exceeded(self, idx):
        with self._lock:
            self._cooldowns[idx] = time.time() + 65
            log.warning(f"Gemini key {idx+1} cooling down 65s")

    def all_on_cooldown(self):
        now = time.time()
        return all(now < self._cooldowns.get(i, 0) for i in range(len(self._clients)))

rotator = KeyRotator()
groq_client = None
openrouter_client = None

def initialize_keys():
    keys = Config.load_keys()
    rotator.initialize(keys)

    global groq_client, openrouter_client

    if Config.GROQ_API_KEY:
        groq_client = OpenAI(
            api_key=Config.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            timeout=30.0
        )
        log.info("Groq client ready")
    else:
        log.warning("No Groq key found")

    if Config.OPENROUTER_API_KEY:
        openrouter_client = OpenAI(
            api_key=Config.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=30.0
        )
        log.info("OpenRouter client ready")
    else:
        log.warning("No OpenRouter key found")

def is_quota_error(e):
    msg = str(e).lower()
    return any(x in msg for x in [
        "quota", "limit", "429", "resource exhausted",
        "rate", "too many", "overloaded", "capacity"
    ])

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

def try_groq_stream(prompt: str, max_tokens: int = 1024, temperature: float = 0.7):
    if not groq_client:
        return False, None
    try:
        log.info("Trying Groq...")
        stream = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        return True, stream
    except Exception as e:
        log.warning(f"Groq failed: {e}")
        return False, None

def try_openrouter_stream(prompt: str, max_tokens: int = 1024, temperature: float = 0.7):
    if not openrouter_client:
        return False, None
    # Try each OpenRouter model in rotation
    tried = set()
    total = len(OPENROUTER_MODELS)
    for _ in range(total):
        model = get_openrouter_model()
        if model in tried:
            continue
        tried.add(model)
        try:
            log.info(f"Trying OpenRouter: {model}")
            stream = openrouter_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                extra_headers={
                    "HTTP-Referer": "https://neurotutor.com", # Optional
                    "X-Title": "NeuroTutor",                 # Optional
                }
            )
            return True, stream
        except Exception as e:
            log.warning(f"OpenRouter {model} failed: {e}")
            continue
    return False, None

def yield_openai_stream(stream):
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            yield f"data: {json.dumps({'text': text})}\n\n"
    yield "data: [DONE]\n\n"

def stream_with_fallbacks(prompt: str, max_tokens: int = 1024, temperature: float = 0.7):
    # 1 — Try Gemini keys
    if not rotator.all_on_cooldown():
        max_attempts = len(Config.GEMINI_API_KEYS)
        for attempt in range(max_attempts):
            if rotator.all_on_cooldown():
                break
            client, idx = rotator.get_client()
            if client is None:
                break
            try:
                log.info(f"Trying Gemini key {idx+1}...")
                response = client.models.generate_content_stream(
                    model=Config.GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "max_output_tokens": max_tokens,
                        "temperature": temperature,
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
                    rotator.mark_exceeded(idx)
                    continue
                else:
                    log.error(f"Gemini error (Key {idx+1}): {e}")
                    continue

    # 2 — Try Groq
    ok, stream = try_groq_stream(prompt, max_tokens, temperature)
    if ok:
        yield from yield_openai_stream(stream)
        return

    # 3 — Try OpenRouter models in rotation
    ok, stream = try_openrouter_stream(prompt, max_tokens, temperature)
    if ok:
        yield from yield_openai_stream(stream)
        return

    # 4 — All failed
    yield f"data: {json.dumps({'text': QUOTA_FINAL})}\n\n"
    yield "data: [DONE]\n\n"

def generate_with_fallback(prompt: str, max_tokens: int = 1024, is_json: bool = True):
    # 1 — Try all Gemini keys in rotation
    if not rotator.all_on_cooldown():
        max_attempts = len(Config.GEMINI_API_KEYS)
        for attempt in range(max_attempts):
            if rotator.all_on_cooldown():
                break
            client, idx = rotator.get_client()
            if client is None:
                break
            try:
                response = client.models.generate_content(
                    model=Config.GEMINI_MODEL,
                    contents=prompt,
                    config={
                        "max_output_tokens": max_tokens,
                        "temperature": 0.5
                    }
                )
                raw = (response.text or '').strip()
                if is_json:
                    raw = raw.replace('```json', '').replace('```', '').strip()
                    return json.loads(raw), None
                return raw, None
            except Exception as e:
                if is_quota_error(e):
                    rotator.mark_exceeded(idx)
                    log.warning(f"Gemini key {idx+1} quota hit during generate, trying next key")
                    continue
                else:
                    log.error(f"Gemini generate error (Key {idx+1}): {e}")
                    continue

    # 2 — Try Groq
    if groq_client:
        try:
            log.info("Quiz trying Groq...")
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.5
            )
            raw = (response.choices[0].message.content or '').strip()
            if is_json:
                raw = raw.replace('```json', '').replace('```', '').strip()
                return json.loads(raw), None
            return raw, None
        except Exception as e:
            log.warning(f"Groq generate failed: {e}")

    # 3 — Try OpenRouter models in rotation
    if openrouter_client:
        tried = set()
        for _ in range(len(OPENROUTER_MODELS)):
            model = get_openrouter_model()
            if model in tried:
                continue
            tried.add(model)
            try:
                log.info(f"Quiz trying OpenRouter: {model}")
                response = openrouter_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.5
                )
                raw = (response.choices[0].message.content or '').strip()
                if is_json:
                    raw = raw.replace('```json', '').replace('```', '').strip()
                    return json.loads(raw), None
                return raw, None
            except Exception as e:
                log.warning(f"OpenRouter {model} generate failed: {e}")
                continue

    return None, QUOTA_FINAL

def stream_response(prompt: str):
    yield from stream_with_fallbacks(prompt)

def stream_debug(code: str):
    from modules.prompts import DEBUG_PROMPT
    prompt = f"{DEBUG_PROMPT}\n\nBroken code to debug:\n```python\n{code}\n```"
    yield from stream_with_fallbacks(prompt, max_tokens=1024, temperature=0.3)

def generate_quiz(topic: str, count: int = 3):
    from modules.prompts import get_quiz_prompt
    prompt = get_quiz_prompt(topic, count)
    return generate_with_fallback(prompt, max_tokens=count * 350)
def generate_roadmap(topic: str, days: int, level: str):
    from modules.prompts import get_roadmap_prompt
    prompt = get_roadmap_prompt(topic, days, level)
    return generate_with_fallback(prompt, max_tokens=days * 200)

def generate_compare(concept_a: str, concept_b: str):
    from modules.prompts import CONCEPT_COMPARE_PROMPT, fill
    prompt = fill(CONCEPT_COMPARE_PROMPT, concept_a=concept_a, concept_b=concept_b)
    return generate_with_fallback(prompt, max_tokens=1000)