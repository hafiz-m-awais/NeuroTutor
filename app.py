import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import google.generativeai as genai
import json

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

if not GEMINI_API_KEY:
    log.error("GEMINI_API_KEY environment variable is not set!")
    raise ValueError("GEMINI_API_KEY is required. Please set it in a .env file.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-3-flash-preview')

SYSTEM_PROMPT = """You are AskAI — an expert AI and Data Science tutor exclusively for Pakistani CS students.

STRICT RULES:
1. ONLY answer questions about: AI, Machine Learning, Deep Learning, Data Science, Python programming, NLP, Computer Vision, or related CS topics.
2. If asked anything else respond with: "I can only help with AI, Machine Learning, Data Science and Python topics!"
3. Always give: simple explanation first, Python code example when relevant, real world analogy.
4. Be conversational, encouraging and remember the conversation context.
5. Keep answers concise but complete. Use bullet points and code blocks.
6. Never produce harmful, political or inappropriate content.
7. You are talking to Pakistani students — be warm, friendly and relatable."""

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AskAI Pakistan — AI Tutor for CS Students</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #f0f2f5;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .header {
    background: #1a1a2e;
    color: white;
    padding: 14px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
  }

  .header-left { display: flex; align-items: center; gap: 12px; }

  .avatar {
    width: 38px; height: 38px;
    background: #4f46e5;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; font-weight: 700; color: white;
  }

  .header h1 { font-size: 16px; font-weight: 600; }
  .header p { font-size: 12px; opacity: 0.6; margin-top: 1px; }

  .status {
    display: flex; align-items: center; gap: 6px;
    font-size: 12px; opacity: 0.8;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #4caf50; }

  .topics-bar {
    background: white;
    border-bottom: 1px solid #e0e0e0;
    padding: 10px 16px;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    flex-shrink: 0;
  }
  .topics-bar::-webkit-scrollbar { display: none; }

  .chip {
    padding: 5px 14px;
    background: #f0f2f5;
    border: 1px solid #e0e0e0;
    border-radius: 20px;
    font-size: 12px;
    cursor: pointer;
    white-space: nowrap;
    color: #444;
    transition: all 0.2s;
    flex-shrink: 0;
  }
  .chip:hover { background: #1a1a2e; color: white; border-color: #1a1a2e; }

  .chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .chat-area::-webkit-scrollbar { width: 4px; }
  .chat-area::-webkit-scrollbar-thumb { background: #ccc; border-radius: 2px; }

  .msg { display: flex; gap: 10px; max-width: 80%; }
  .msg.user { align-self: flex-end; flex-direction: row-reverse; }
  .msg.bot { align-self: flex-start; }

  .msg-avatar {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 700;
    flex-shrink: 0; margin-top: 2px;
  }
  .msg.bot .msg-avatar { background: #4f46e5; color: white; }
  .msg.user .msg-avatar { background: #1a1a2e; color: white; }

  .bubble {
    padding: 12px 16px;
    border-radius: 18px;
    font-size: 14px;
    line-height: 1.7;
    max-width: 100%;
    word-wrap: break-word;
  }

  .msg.user .bubble {
    background: #1a1a2e;
    color: white;
    border-bottom-right-radius: 4px;
  }

  .msg.bot .bubble {
    background: white;
    color: #1a1a1a;
    border: 1px solid #e8e8e8;
    border-bottom-left-radius: 4px;
  }

  .bubble pre {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 13px;
    margin: 8px 0;
    white-space: pre-wrap;
  }

  .bubble code {
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    color: #d63384;
  }

  .bubble pre code {
    background: transparent;
    padding: 0;
    color: #cdd6f4;
  }

  .bubble p { margin-bottom: 8px; }
  .bubble p:last-child { margin-bottom: 0; }
  .bubble ul, .bubble ol { padding-left: 20px; margin: 6px 0; }
  .bubble li { margin-bottom: 4px; }
  .bubble h3 { font-size: 14px; margin: 10px 0 6px; color: #1a1a2e; }

  .typing {
    display: flex; gap: 4px; align-items: center; padding: 4px 0;
  }
  .typing span {
    width: 7px; height: 7px;
    background: #aaa; border-radius: 50%;
    animation: bounce 1.2s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }

  .welcome {
    text-align: center;
    padding: 40px 20px;
    color: #888;
  }
  .welcome .icon {
    width: 56px; height: 56px;
    background: #4f46e5;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px; margin: 0 auto 16px;
    color: white; font-weight: 700;
  }
  .welcome h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 8px; font-weight: 600; }
  .welcome p { font-size: 14px; line-height: 1.6; max-width: 340px; margin: 0 auto; }

  .input-area {
    background: white;
    border-top: 1px solid #e0e0e0;
    padding: 12px 16px;
    display: flex;
    gap: 10px;
    align-items: flex-end;
    flex-shrink: 0;
  }

  textarea#input {
    flex: 1;
    border: 1px solid #e0e0e0;
    border-radius: 22px;
    padding: 10px 16px;
    font-size: 14px;
    font-family: inherit;
    resize: none;
    outline: none;
    max-height: 120px;
    min-height: 44px;
    line-height: 1.5;
    transition: border-color 0.2s;
    overflow-y: auto;
  }
  textarea#input:focus { border-color: #4f46e5; }

  .send-btn {
    width: 44px; height: 44px;
    background: #1a1a2e;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    transition: opacity 0.2s;
    flex-shrink: 0;
  }
  .send-btn:hover { opacity: 0.85; }
  .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .send-btn svg { width: 18px; height: 18px; fill: white; }

  .clear-btn {
    padding: 8px 14px;
    background: transparent;
    border: 1px solid #e0e0e0;
    border-radius: 20px;
    font-size: 12px;
    color: #888;
    cursor: pointer;
    white-space: nowrap;
  }
  .clear-btn:hover { border-color: #aaa; color: #444; }

  @media (max-width: 600px) {
    .msg { max-width: 92%; }
  }
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <div class="avatar">A</div>
    <div>
      <h1>AskAI Pakistan</h1>
      <p>Free AI tutor for Pakistani CS students</p>
    </div>
  </div>
  <div class="status">
    <div class="dot"></div>
    Online
  </div>
</div>

<div class="topics-bar">
  <span class="chip" onclick="sendChip('Explain transformers with a Python example')">Transformers</span>
  <span class="chip" onclick="sendChip('Explain backpropagation step by step')">Backpropagation</span>
  <span class="chip" onclick="sendChip('What is RAG and how does it work?')">RAG</span>
  <span class="chip" onclick="sendChip('Explain attention mechanism simply')">Attention</span>
  <span class="chip" onclick="sendChip('What is gradient descent with Python code?')">Gradient Descent</span>
  <span class="chip" onclick="sendChip('Explain CNNs with an example')">CNNs</span>
  <span class="chip" onclick="sendChip('What is overfitting and how to prevent it?')">Overfitting</span>
  <span class="chip" onclick="sendChip('Explain word embeddings simply')">Embeddings</span>
  <span class="chip" onclick="sendChip('Difference between LSTM and GRU?')">LSTM vs GRU</span>
  <span class="chip" onclick="sendChip('How does BERT work?')">BERT</span>
  <span class="chip" onclick="sendChip('Explain PyTorch vs TensorFlow')">PyTorch vs TF</span>
  <span class="chip" onclick="sendChip('What is fine-tuning in LLMs?')">Fine-tuning</span>
</div>

<div class="chat-area" id="chat">
  <div class="welcome" id="welcome">
    <div class="icon">A</div>
    <h2>Assalam o Alaikum!</h2>
    <p>I'm your free AI tutor for Machine Learning and Data Science. Ask me anything — I'll explain it simply with code examples.</p>
  </div>
</div>

<div class="input-area">
  <button class="clear-btn" onclick="clearChat()">New chat</button>
  <textarea id="input" placeholder="Ask any AI or ML question..." rows="1" maxlength="500"></textarea>
  <button class="send-btn" id="send-btn" onclick="sendMessage()">
    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
    </svg>
  </button>
</div>

<script>
  let conversationHistory = [];
  let isStreaming = false;

  const chatEl = document.getElementById('chat');
  const inputEl = document.getElementById('input');
  const sendBtn = document.getElementById('send-btn');

  inputEl.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
  });

  inputEl.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  function sendChip(text) {
    inputEl.value = text;
    sendMessage();
  }

  function clearChat() {
    conversationHistory = [];
    chatEl.innerHTML = `
      <div class="welcome" id="welcome">
        <div class="icon">A</div>
        <h2>Assalam o Alaikum!</h2>
        <p>I'm your free AI tutor for Machine Learning and Data Science. Ask me anything — I'll explain it simply with code examples.</p>
      </div>`;
  }

  function addMessage(role, text) {
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.remove();

    const isUser = role === 'user';
    const div = document.createElement('div');
    div.className = `msg ${isUser ? 'user' : 'bot'}`;

    const initial = isUser ? 'U' : 'A';
    div.innerHTML = `
      <div class="msg-avatar">${initial}</div>
      <div class="bubble" id="bubble-${Date.now()}">${isUser ? escapeHtml(text) : ''}</div>
    `;
    chatEl.appendChild(div);
    scrollBottom();
    return div.querySelector('.bubble');
  }

  function addTyping() {
    const welcome = document.getElementById('welcome');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    div.className = 'msg bot';
    div.id = 'typing-indicator';
    div.innerHTML = `
      <div class="msg-avatar">A</div>
      <div class="bubble">
        <div class="typing">
          <span></span><span></span><span></span>
        </div>
      </div>`;
    chatEl.appendChild(div);
    scrollBottom();
  }

  function removeTyping() {
    const t = document.getElementById('typing-indicator');
    if (t) t.remove();
  }

  function scrollBottom() {
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function escapeHtml(text) {
    return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function formatText(text) {
    text = text.replace(/```(\w+)?\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/^### (.*)/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*)/gm, '<h3>$1</h3>');
    text = text.replace(/^\* (.*)/gm, '<li>$1</li>');
    text = text.replace(/^- (.*)/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    text = text.replace(/\n\n/g, '</p><p>');
    text = '<p>' + text + '</p>';
    text = text.replace(/<p><\/p>/g, '');
    text = text.replace(/<p>(<pre>)/g, '$1');
    text = text.replace(/<\/pre><\/p>/g, '</pre>');
    text = text.replace(/<p>(<h3>)/g, '$1');
    text = text.replace(/<\/h3><\/p>/g, '</h3>');
    text = text.replace(/<p>(<ul>)/g, '$1');
    text = text.replace(/<\/ul><\/p>/g, '</ul>');
    return text;
  }

  async function sendMessage() {
    const question = inputEl.value.trim();
    if (!question || isStreaming) return;
    if (question.length < 3) return;

    isStreaming = true;
    sendBtn.disabled = true;
    inputEl.value = '';
    inputEl.style.height = 'auto';

    addMessage('user', question);
    conversationHistory.push({ role: 'user', content: question });

    addTyping();

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          history: conversationHistory.slice(-10)
        })
      });

      if (!res.ok) {
        removeTyping();
        const err = await res.json();
        addMessage('bot', err.error || 'Something went wrong. Please try again.');
        return;
      }

      removeTyping();
      const bubble = addMessage('bot', '');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.text) {
                fullText += parsed.text;
                bubble.innerHTML = formatText(fullText);
                scrollBottom();
              }
            } catch(e) {}
          }
        }
      }

      conversationHistory.push({ role: 'assistant', content: fullText });

    } catch (err) {
      removeTyping();
      addMessage('bot', 'Connection error. Please try again.');
    } finally {
      isStreaming = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  }
</script>
</body>
</html>
"""

@app.route('/')
def home():
    log.info("Home page accessed")
    return render_template_string(HTML)

@app.route('/ask', methods=['POST'])
@limiter.limit("15 per minute")
def ask():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400

        question = data.get('question', '').strip()
        history = data.get('history', [])

        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        if len(question) < 3:
            return jsonify({'error': 'Question is too short'}), 400
        if len(question) > 500:
            return jsonify({'error': 'Question too long. Max 500 characters.'}), 400

        messages = [{'role': 'user', 'parts': [SYSTEM_PROMPT + '\n\nYou are now starting a tutoring session.']}]

        for msg in history[:-1]:
            role = 'user' if msg['role'] == 'user' else 'model'
            messages.append({'role': role, 'parts': [msg['content']]})

        log.info(f"Question: {question[:60]}...")

        def generate():
            try:
                chat = model.start_chat(history=messages)
                response = chat.send_message(question, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield f"data: {json.dumps({'text': chunk.text})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                log.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'text': 'Sorry, something went wrong. Please try again.'})}\n\n"
                yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        log.error(f"Error: {str(e)}", exc_info=True)
        error_msg = str(e) if str(e) else 'Something went wrong. Please try again.'
        return jsonify({'error': error_msg}), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    log.info(f"Starting {APP_NAME}")
    app.run(debug=False, port=7860, host='0.0.0.0')