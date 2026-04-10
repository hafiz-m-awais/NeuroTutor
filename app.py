import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('askai.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "20 per hour"],
    storage_uri="memory://"
)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
APP_NAME = os.getenv('APP_NAME', 'AskAI Pakistan')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """You are an AI and Data Science tutor exclusively for Pakistani CS students.

STRICT RULES — follow these without exception:
1. ONLY answer questions about: AI, Machine Learning, Deep Learning, Data Science, Python programming, NLP, Computer Vision, or related CS topics.
2. If the question is about ANYTHING else — respond with exactly: "I can only help with AI, Machine Learning, Data Science and Python topics. Please ask me something related to these subjects!"
3. Always include a simple explanation, a Python code example when relevant, and a real world analogy.
4. Keep answers practical and encouraging for students learning on basic hardware in Pakistan.
5. Never produce harmful, political or inappropriate content.

Remember: You are a specialized tutor, not a general assistant."""

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AskAI Pakistan — Free AI Tutor for CS Students</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, sans-serif; background: #f8f9fa; color: #1a1a1a; min-height: 100vh; }
  .header { background: #1a1a2e; color: white; padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; }
  .header h1 { font-size: 20px; font-weight: 600; }
  .header p { font-size: 13px; opacity: 0.65; margin-top: 3px; }
  .status { display: flex; align-items: center; gap: 6px; font-size: 12px; opacity: 0.8; }
  .dot-green { width: 8px; height: 8px; border-radius: 50%; background: #4caf50; }
  .container { max-width: 820px; margin: 32px auto; padding: 0 16px; }
  .topics { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
  .topic-btn { padding: 6px 14px; background: white; border: 1px solid #ddd; border-radius: 20px; font-size: 13px; cursor: pointer; transition: all 0.2s; }
  .topic-btn:hover { background: #1a1a2e; color: white; border-color: #1a1a2e; }
  .input-area { background: white; border-radius: 12px; border: 1px solid #e0e0e0; padding: 20px; margin-bottom: 20px; }
  .input-area label { font-size: 13px; color: #666; display: block; margin-bottom: 8px; }
  textarea { width: 100%; border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px; font-size: 15px; resize: vertical; min-height: 80px; font-family: inherit; outline: none; transition: border-color 0.2s; }
  textarea:focus { border-color: #1a1a2e; }
  .btn-row { display: flex; gap: 10px; margin-top: 12px; align-items: center; }
  button.ask-btn { background: #1a1a2e; color: white; border: none; padding: 11px 28px; border-radius: 8px; font-size: 14px; cursor: pointer; font-weight: 500; transition: opacity 0.2s; }
  button.ask-btn:hover { opacity: 0.85; }
  button.ask-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  button.clear-btn { background: transparent; color: #888; border: 1px solid #ddd; padding: 11px 20px; border-radius: 8px; font-size: 14px; cursor: pointer; }
  button.clear-btn:hover { border-color: #999; color: #444; }
  .char-count { margin-left: auto; font-size: 12px; color: #aaa; }
  .answer-box { background: white; border-radius: 12px; border: 1px solid #e0e0e0; padding: 24px; display: none; margin-bottom: 20px; }
  .answer-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .answer-header h3 { font-size: 15px; color: #1a1a2e; font-weight: 600; }
  .answer-time { font-size: 11px; color: #aaa; }
  .answer-content { font-size: 15px; line-height: 1.8; white-space: pre-wrap; }
  .error-box { background: #fff5f5; border: 1px solid #ffcdd2; border-radius: 8px; padding: 14px; color: #c62828; font-size: 14px; display: none; margin-bottom: 16px; }
  .loading-box { background: #f0f4ff; border: 1px solid #c5cae9; border-radius: 8px; padding: 14px; color: #3949ab; font-size: 14px; display: none; margin-bottom: 16px; }
  .history { background: white; border-radius: 12px; border: 1px solid #e0e0e0; padding: 20px; }
  .history h3 { font-size: 14px; color: #666; margin-bottom: 12px; font-weight: 500; }
  .history-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; cursor: pointer; }
  .history-item:last-child { border-bottom: none; }
  .history-item:hover { opacity: 0.7; }
  .history-q { font-size: 13px; color: #1a1a2e; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .history-t { font-size: 11px; color: #aaa; margin-top: 2px; }
  .empty-history { font-size: 13px; color: #bbb; text-align: center; padding: 12px 0; }
  .footer { text-align: center; padding: 28px; font-size: 12px; color: #aaa; }
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>AskAI Pakistan</h1>
    <p>Free AI tutor for Pakistani CS students — no signup needed</p>
  </div>
  <div class="status">
    <div class="dot-green"></div>
    Online
  </div>
</div>

<div class="container">
  <div class="topics">
    <button class="topic-btn" onclick="setTopic('Explain transformers in simple words with a Python example')">Transformers</button>
    <button class="topic-btn" onclick="setTopic('Explain backpropagation step by step with code')">Backpropagation</button>
    <button class="topic-btn" onclick="setTopic('What is RAG and how does it work?')">RAG</button>
    <button class="topic-btn" onclick="setTopic('Explain attention mechanism with a simple example')">Attention</button>
    <button class="topic-btn" onclick="setTopic('What is gradient descent? Explain with Python code')">Gradient Descent</button>
    <button class="topic-btn" onclick="setTopic('Explain CNNs with a simple image classification example')">CNNs</button>
    <button class="topic-btn" onclick="setTopic('What is overfitting and how to prevent it?')">Overfitting</button>
    <button class="topic-btn" onclick="setTopic('Explain word embeddings and Word2Vec simply')">Embeddings</button>
    <button class="topic-btn" onclick="setTopic('What is the difference between LSTM and GRU?')">LSTM vs GRU</button>
    <button class="topic-btn" onclick="setTopic('Explain how BERT works in simple terms')">BERT</button>
  </div>

  <div class="input-area">
    <label>Ask any AI or Data Science question</label>
    <textarea id="question" placeholder="e.g. Explain LSTMs with a simple Python example..." maxlength="500" oninput="updateCount()"></textarea>
    <div class="btn-row">
      <button class="ask-btn" onclick="askQuestion()" id="ask-btn">Ask AI</button>
      <button class="clear-btn" onclick="clearAll()">Clear</button>
      <span class="char-count" id="char-count">0 / 500</span>
    </div>
  </div>

  <div class="error-box" id="error-box"></div>
  <div class="loading-box" id="loading-box">AI is thinking... usually takes 3-5 seconds.</div>

  <div class="answer-box" id="answer-box">
    <div class="answer-header">
      <h3>Answer</h3>
      <span class="answer-time" id="answer-time"></span>
    </div>
    <div class="answer-content" id="answer-content"></div>
  </div>

  <div class="history" id="history-box">
    <h3>Recent questions</h3>
    <div id="history-list"><div class="empty-history">No questions yet</div></div>
  </div>
</div>

<div class="footer">Built by Awais · Free for all Pakistani CS students · Powered by Gemini AI</div>

<script>
  let history = [];

  function updateCount() {
    const q = document.getElementById('question').value;
    document.getElementById('char-count').textContent = q.length + ' / 500';
  }

  function setTopic(text) {
    document.getElementById('question').value = text;
    updateCount();
    document.getElementById('question').focus();
  }

  function clearAll() {
    document.getElementById('question').value = '';
    document.getElementById('answer-box').style.display = 'none';
    document.getElementById('error-box').style.display = 'none';
    updateCount();
  }

  function showError(msg) {
    const box = document.getElementById('error-box');
    box.textContent = msg;
    box.style.display = 'block';
    setTimeout(() => box.style.display = 'none', 5000);
  }

  function addToHistory(question) {
    history.unshift({ q: question, t: new Date().toLocaleTimeString() });
    if (history.length > 5) history.pop();
    const list = document.getElementById('history-list');
    list.innerHTML = history.map(h => `
      <div class="history-item" onclick="setTopic('${h.q.replace(/'/g, "\\'")}')">
        <div class="history-q">${h.q}</div>
        <div class="history-t">${h.t}</div>
      </div>
    `).join('');
  }

  async function askQuestion() {
    const question = document.getElementById('question').value.trim();
    if (!question) { showError('Please type a question first.'); return; }
    if (question.length < 5) { showError('Question is too short. Please be more specific.'); return; }

    const btn = document.getElementById('ask-btn');
    const answerBox = document.getElementById('answer-box');
    const content = document.getElementById('answer-content');
    const loading = document.getElementById('loading-box');
    const errorBox = document.getElementById('error-box');

    btn.disabled = true;
    btn.textContent = 'Thinking...';
    loading.style.display = 'block';
    answerBox.style.display = 'none';
    errorBox.style.display = 'none';

    const start = Date.now();

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      });

      const data = await res.json();

      if (!res.ok) {
        showError(data.error || 'Something went wrong. Please try again.');
        return;
      }

      const elapsed = ((Date.now() - start) / 1000).toFixed(1);
      content.textContent = data.answer;
      document.getElementById('answer-time').textContent = `Answered in ${elapsed}s`;
      answerBox.style.display = 'block';
      addToHistory(question);
      answerBox.scrollIntoView({ behavior: 'smooth' });

    } catch (err) {
      showError('Connection error. Please try again.');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Ask AI';
      loading.style.display = 'none';
    }
  }

  document.getElementById('question').addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') askQuestion();
  });
</script>
</body>
</html>
"""

@app.route('/')
def home():
    log.info("Home page accessed")
    return render_template_string(HTML)

@app.route('/ask', methods=['POST'])
@limiter.limit("10 per minute")
def ask():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400

        question = data.get('question', '').strip()

        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        if len(question) < 5:
            return jsonify({'error': 'Question is too short'}), 400
        if len(question) > 500:
            return jsonify({'error': 'Question is too long. Max 500 characters.'}), 400

        log.info(f"Question: {question[:60]}...")

        full_prompt = f"{SYSTEM_PROMPT}\n\nStudent question: {question}"
        response = model.generate_content(full_prompt)
        answer = response.text

        log.info(f"Answer generated — length: {len(answer)}")
        return jsonify({'answer': answer})

    except Exception as e:
        log.error(f"Error: {e}")
        return jsonify({'error': 'Something went wrong. Please try again.'}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    log.info(f"Starting {APP_NAME}")
    app.run(debug=False, port=7860, host='0.0.0.0')