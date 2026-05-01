# NeuroTutor — Project Documentation

Last updated: 2026-05-01

## Project Summary

NeuroTutor is an open-source AI-powered tutoring web app designed to help Pakistani computer-science students learn, practice, and build confidence. It provides on-demand quiz generation, code explanations, step-by-step learning roadmaps, document summarization, and interactive chat with model-backed assistance.

Quick links
- Hugging Face Space: https://huggingface.co/spaces/awaisriaz/NeuroTutor
- GitHub repository: https://github.com/hafiz-m-awais/NeuroTutor

## Key Features

- Generate practice quizzes and answers from prompts
- Explain code and debugging steps
- Build personalized study roadmaps
- Upload documents (PDF/DOCX/XLSX/CSV) and ask questions or summarize
- Persistent user accounts and chat history
- Rate limits and token caps to control API usage

## Architecture Overview

The app is a Flask web application with a thin frontend and modular backend. Major components:

- `app.py` — Flask application, routes, auth, and request handling
- `modules/` — business logic modules:
  - `ai.py` — AI provider abstraction, key rotation, prompts and generation helpers
  - `file_processor.py` — document extraction and parsing
  - `models.py` — SQLAlchemy ORM models (`User`, `Chat`, `Message`)
  - `prompts.py` — system & prompt templates
  - `validators.py` — input validators
- `templates/`, `static/` — frontend HTML, CSS, JS
- SQLite by default (configured via `DATABASE_URL` for production DBs)
- Hosted on Hugging Face Spaces (origin) and mirrored to GitHub (github remote)

## Tech Stack

- Python 3.11
- Flask 3.x
- Flask-Login, Flask-Limiter, Flask-SQLAlchemy
- google-genai (Gemini), OpenAI-compatible fallbacks (Groq/OpenRouter)
- cachetools, openpyxl
- Gunicorn / Uvicorn for production

## Project Layout (top-level)

```
app.py
config.py
requirements.txt
PROJECT_REPORT.md
PROJECT_DOCUMENTATION.md  # (this file)
modules/
templates/
static/
uploads/
```

## Environment & Configuration

Important environment variables (examples):

- `SECRET_KEY` — Flask secret. Do NOT commit to source. If missing, app warns and falls back to a generated value (not recommended).
- `DATABASE_URL` — SQLAlchemy database URL (defaults to SQLite in `instance/`)
- `GEMINI_API_KEY_1..10` — Optional Gemini keys for rotation
- `OPENAI_API_KEY` / `OPENROUTER_API_KEY` — Fallback provider keys
- `ALLOWED_ORIGINS` — comma-separated additional CORS origins
- `RATE_LIMIT_PER_HOUR`, `RATE_LIMIT_PER_DAY` — override default rate-limits

Store secrets in your deployment platform's secret manager (Hugging Face Spaces UI, GitHub Actions secrets, or environment manager).

## Local Setup (Developer)

1. Create & activate virtualenv

Windows PowerShell

```powershell
python -m venv venv
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. (Optional) Verify import

```bash
python -c "import app; print('OK')"
```

3. Run development server

```bash
# Unix
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=8000

# Windows (cmd)
set FLASK_APP=app.py
set FLASK_ENV=development
flask run --host=0.0.0.0 --port=8000
```

Production note: the project has been deployed to Hugging Face Spaces and can be run with `gunicorn` or a WSGI server. Example (Linux):

```bash
gunicorn --bind 0.0.0.0:7860 --timeout 120 app:app
```

## Deployment

- Hugging Face Spaces: push to the `origin` remote; configure Secrets in the Space settings (API keys, `SECRET_KEY`, `DATABASE_URL` as needed).
- GitHub: push to `github` remote; use GitHub Actions or your CI to run tests and formatting.

## API / Routes (summary)

- `GET /` — Public homepage
- `GET /register`, `POST /register` — Register new users
- `GET /login`, `POST /login` — Login
- `GET /logout` — Logout (redirects to login)
- `POST /ask` — Chat / ask AI (requires authentication)
- `POST /quiz` — Generate quiz from prompt (requires authentication)
- `POST /roadmap` — Generate roadmap for a topic (requires authentication)
- `POST /compare` — Compare answers or approaches
- `POST /upload` — Upload document
- `POST /ask-document` — Ask questions about uploaded document
- `POST /summarize-document` — Summarize uploaded document

All AI-related endpoints are protected with `@login_required` and are rate-limited.

## Security & Privacy

- Authentication: `Flask-Login` for session management; ensure `SECRET_KEY` is stable across restarts.
- IP & Rate Limiting: `Flask-Limiter` with a safe `get_real_ip()` implementation that ignores untrusted `X-Forwarded-For` headers unless proxied by localhost.
- Logging: user content/PII is redacted from logs; logs include only generic operational information.
- Token/Cost Control: token caps for quiz and roadmap endpoints to prevent runaway costs.

## Recent Fixes and Maintenance Notes

This project recently underwent a security and stability audit. Key fixes include:

- Stabilized `SECRET_KEY` handling to avoid session invalidation on restart
- Added `@login_required` to all AI endpoints
- Prevented IP spoofing via `X-Forwarded-For` hardening
- Added input validators for email and password strength
- Replaced fragile JSON parsing with a robust parser using regex fallback
- Incremental chat save to avoid re-writing entire chat history
- Replaced `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`
- Pinned `openpyxl` and `cachetools` versions in `requirements.txt`

Refer to `PROJECT_REPORT.md` for a detailed change log and the audit summary.

## Roadmap & TODOs

- Wire up Roman‑Urdu mode toggle (UI + backend flag) — planned next
- Add end-to-end tests and CI
- Add multi-language UI and i18n support
- Improve UX for mobile devices
- Add analytics dashboard for usage & cost tracking

## Contributing

1. Fork the repository and create a feature branch
2. Run linters / formatters and tests locally
3. Open a PR with a clear description and small atomic changes

Developer conventions
- Follow existing code style (avoid one-letter variable names; keep changes minimal and focused)
- Write unit tests for new logic where reasonable

## Troubleshooting

- Port conflicts: if port is in use, kill conflicting Python processes (Windows):

```powershell
taskkill /F /IM python.exe
```

- Missing `openpyxl` errors: ensure `requirements.txt` is installed with pinned versions.

## Testing

Run quick import smoke test:

```bash
python -c "import app; print('OK')"
```

Add `pytest` tests and CI in future iterations.

## License

See repository `LICENSE` file. If none exists, consider adding an OSI-approved license (MIT is common for starter projects).

## Contact

Open issues or PRs on GitHub: https://github.com/hafiz-m-awais/NeuroTutor

---

This file was generated to provide a single-source project overview. If you want, I can also update `README.md` or `PROJECT_REPORT.md` with a condensed version of this content.
