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
      <p>I'm your free AI tutor for Machine Learning and Data Science. Ask me anything!</p>
    </div>`;
}

function addMessage(role, text) {
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();

  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `msg ${isUser ? 'user' : 'bot'}`;
  div.innerHTML = `
    <div class="msg-avatar">${isUser ? 'U' : 'A'}</div>
    <div class="bubble">${isUser ? escapeHtml(text) : ''}</div>
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
      <div class="typing"><span></span><span></span><span></span></div>
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
        history: conversationHistory.slice(-Config.MAX_HISTORY)
      })
    });

    if (!res.ok) {
      removeTyping();
      const err = await res.json();
      addMessage('bot', err.error || 'Something went wrong.');
      return;
    }

    removeTyping();
    const bubble = addMessage('bot', '');
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') break;
          try {
            const parsed = JSON.parse(data);
            if (parsed.text) {
              fullText += parsed.text;
              bubble.innerHTML = formatText(fullText);
              enhanceCodeBlocks(bubble);
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