# 📄 Detailed Project Report: NeuroTutor

## 1. Project Overview & Vision
**NeuroTutor** (formerly *AskAI Pakistan*) is a specialized, real-time conversational AI tutor built specifically for Pakistani Computer Science and Data Science students. Designed to act as a knowledgeable senior peer, the application exclusively focuses on answering educational questions related to Artificial Intelligence, Machine Learning, Deep Learning, Data Science, and Python. It securely and politely declines any off-topic queries, ensuring the tool remains highly focused and cost-effective.

## 2. Core Architecture & Tech Stack
The project follows a modular, lightweight, and scalable web architecture:
- **Backend Framework:** Python 3.9+ with Flask.
- **AI Engine:** Google Gemini API (`gemini-2.5-flash` model).
- **Rate Limiting & Security:** `Flask-Limiter` (using in-memory storage).
- **Frontend:** Vanilla HTML, CSS, JavaScript (utilizing Pyodide for in-browser execution if needed).
- **Deployment/Hosting:** Dockerized for portability, employing `gunicorn` for production-grade serving, and hosted seamlessly on Hugging Face Spaces.

---

## 3. Current Features & Implementations (Checklist)

- [x] **Real-Time Streaming (Server-Sent Events):** The backend utilizes `stream_with_context` in Flask to stream Gemini API responses in chunks back to the client using SSE. This heavily reduces perceived latency and creates a dynamic chat experience.
- [x] **Domain-Specific "Guardrails":** The system utilizes a heavily tuned prompt file (`modules/prompts.py`) that strictly instructs the Gemini model to stay within the boundaries of CS, AI, ML, Data Science, and Python.
- [x] **Context-Aware Memory:** Through `config.py`, the system remembers up to 4 recent interactions (`MAX_HISTORY = 4`). This allows the AI to maintain conversation flow and reference previous steps in a debugging session without exhausting token limits.
- [x] **Strict Input Validation:** Every input is validated (`modules/validators.py`) to ensure it is between 3 and 500 characters, preventing payload bloat.
- [x] **Robust Rate Limiting:** Network requests are throttled using `Flask-Limiter` (15/min, 20/hour, 100/day) to prevent abuse, bot spam, and API overuse.
- [x] **Fail-Fast Configuration:** The application checks for vital environment variables (like `GEMINI_API_KEY`) upon startup and crashes instantly with a clean error log if they are missing, preventing faulty deployments.
- [x] **Local Browser Storage:** The vanilla JavaScript frontend securely saves user data locally:
  - Preserves user UI preference for light/dark mode (`neurotutor_dark_mode`).
  - Serializes and retrieves previous chat histories (`neurotutor_chats`), allowing users to return to previous conversations seamlessly.
- [x] **Syntax Highlighting & Formatting:** Renders AI code responses properly using markdown parsing and syntax highlighting blocks (`codeblocks.js`).

---

## 4. Project Structure Breakdown

```text
├── app.py                 # Main Flask application and routing, SSE streaming endpoint
├── config.py              # Centralized configuration (temperature, rate limits, models)
├── Dockerfile             # Multi-stage container setup for Hugging Face Spaces
├── requirements.txt       # Python dependencies
├── modules/
│   ├── ai.py              # Gemini API client, chunk handling, continuous streaming logic
│   ├── prompts.py         # AI System instructions and guardrail guidelines
│   └── validators.py      # Input sanitation and min/max length validation
├── static/                # Frontend assets
│   ├── css/               # Styling for chat layout and dark/light modes
│   ├── js/                # Client-side logic for API calling, UI rendering, local storage
└── templates/
    └── index.html         # Main Chat Interface UI
```

---

## 5. Security & Cost Optimization Summary
NeuroTutor is designed to run predictably on platforms like Hugging Face without surprise costs:
1. **Input Limits:** Capped at 500 characters to prevent prompt-injection attacks.
2. **Output Token Limits:** Responses are capped at `1024` tokens to prevent runaway generation.
3. **Daily Quotas:** A hard cap of 100 total requests per user IP per day drastically limits API abuse.
4. **Context Window Limitations:** The AI only sends the last 4 messages back to Gemini on each request, heavily reducing the number of tokens spent per turn compared to sending the entire history.

---

## 6. Future Roadmap & Proposed Enhancements

As the project scales, here are several features that can be added to enhance NeuroTutor:

### 🚀 Phase 1: Authentication & Databases
- [ ] **User Authentication:** Add Google OAuth or traditional email/password login to sync chat histories across devices rather than relying solely on browser LocalStorage.
- [ ] **Persistent Database:** Migrate from LocalStorage and Memory logs to a real database (PostgreSQL or MongoDB) to store chat sessions, user preferences, and usage analytics permanently.

### 🧠 Phase 2: AI Enhancements
- [ ] **RAG (Retrieval-Augmented Generation):** Integrate a vector database (like Pinecone or Chroma) and load it with University curriculum slides, specific CS textbooks, and past exam papers to make the AI's answers hyper-specific to Pakistani university syllabuses.
- [ ] **Multi-Model Support:** Create a toggle in the UI allowing users to switch between Gemini, OpenAI (ChatGPT), or local open-source models (like LLaMA 3) depending on the complexity of their question.

### 💻 Phase 3: Developer & UX Tools
- [ ] **Interactive Code Execution:** Enhance the Pyodide frontend integration so users can actually run the Python snippets the AI generates directly inside the browser chat window.
- [ ] **Export/Share Conversations:** Add a "Share Chat" button that generates a temporary public link or exports the chat as a highly readable PDF/Markdown file for study notes.
- [ ] **Voice Input/Output:** Integrate Web Speech API so students can ask questions using audio (especially useful for accessibility or mobile users).