---
title: NeuroTutor
emoji: 🧠
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
license: mit
---

# 🤖 NeuroTutor

![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-black?style=for-the-badge&logo=flask)
![Gemini API](https://img.shields.io/badge/Google%20Gemini-AI-orange?style=for-the-badge&logo=google)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)

NeuroTutor is a real-time, conversational AI tutor built specifically for Pakistani Computer Science and Data Science students. Designed to act like a helpful senior peer, it strictly focuses on answering questions related to AI, Machine Learning, Deep Learning, Data Science, and Python.

---

## 📹 Demo
![NeuroTutor Demo](Demo.mp4)

---

## ✨ Features

- **Domain-Specific Tutoring:** Strictly bound to AI, ML, Data Science, and Python. NeuroTutor will politely decline off-topic questions.
- **Real-Time Streaming:** Powered by the Google Gemini API, answers are streamed in real-time to the UI (using Server-Sent Events) for a seamless, fast experience.
- **Context-Aware Memory:** Remembers the conversation history, user goals, and names to provide highly personalized, conversational assistance.
- **Rate-Limiting & Security:** Protected by `Flask-Limiter` along with robust input constraints to prevent abuse.
- **Production Ready:** Fully containerized with Docker and configured to use `gunicorn` for robust deployment.
- **Dark Mode UI:** Modern, responsive frontend equipped with dark mode controls, code execution/copying blocks, and sidebars.

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, Flask-Limiter
- **AI SDK:** Google GenAI (`google-genai`)
- **Frontend:** HTML, CSS, JavaScript (Vanilla) + Pyodide (for in-browser execution)
- **Deployment:** Docker, Gunicorn, HuggingFace Spaces

## 📂 Project Structure

```text
├── app.py                 # Main Flask application and routing
├── config.py              # Environment configuration & limits
├── Dockerfile             # Container configuration
├── requirements.txt       # Python dependencies
├── modules/
│   ├── ai.py              # Gemini API client, chunk handling, and continuous streaming logic
│   ├── prompts.py         # AI System instructions and memory guidelines
│   └── validators.py      # Request sanitation and min/max length validation
├── static/                # Frontend assets (CSS & JS)
│   ├── css/
│   ├── js/
└── templates/
    └── index.html         # Main web interface
```

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- A Google Gemini API Key

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/awaisriaz/NeuroTutor.git
   cd NeuroTutor
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and add your Gemini API Key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **Run the Application:**
   ```bash
   python app.py
   ```
   The application will start on `http://localhost:7860`.

### Docker Deployment

To build and run the application using Docker:

```bash
docker build -t neurotutor .
docker run -p 7860:7860 --env-file .env neurotutor
```

---

## 🤝 Contributing
Contributions are always welcome! 
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📬 Contact
**Author:** [Your Name / Awais]  
If you have any questions or feedback, feel free to reach out via GitHub Issues.

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
