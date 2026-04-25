let conversationHistory = [];
let isStreaming = false;
let hasActiveDocument = false;

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
  startNewChat();
}

function addMessage(role, text) {
  const welcome = document.getElementById('welcome');
  if (welcome) welcome.remove();

  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `msg ${isUser ? 'user' : 'bot'}`;
  div.innerHTML = `
    <div class="msg-avatar">${isUser ? 'U' : 'N'}</div>
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
    <div class="msg-avatar">N</div>
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

// Configure marked once for the whole app
if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks: true, gfm: true });
}

function formatText(text) {
  if (typeof marked !== 'undefined') {
    return marked.parse(text);
  }
  // Minimal fallback if CDN fails to load
  return '<p>' + text.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>') + '</p>';
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
    const endpoint = hasActiveDocument ? '/ask-document' : '/ask';

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        question,
        history: hasActiveDocument ? [] : conversationHistory.slice(-Config.MAX_HISTORY * 2)
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
    saveCurrentChat(conversationHistory);

  } catch (err) {
    removeTyping();
    addMessage('bot', 'Connection error. Please try again.');
  } finally {
    isStreaming = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

async function handleChatAttachment(input) {
  const file = input.files[0];
  if (!file) return;

  if (file.size > 10 * 1024 * 1024) {
    alert('File is too large. Max size is 10MB.');
    input.value = '';
    return;
  }

  // Show UI preview
  document.getElementById('chat-attachment-name').textContent = file.name;
  document.getElementById('chat-attachment-preview').style.display = 'flex';
  hasActiveDocument = true;

  // Auto-upload the file
  const formData = new FormData();
  formData.append('file', file);

  const bubble = addMessage('bot', '');
  bubble.innerHTML = '<span class="output-loading">Uploading and analyzing document...</span>';
  scrollBottom();

  try {
    const res = await fetch('/upload', {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Upload failed');
    }

    const data = await res.json();
    const mdSummary = `📄 **Document Uploaded:** \`${data.filename}\`\n\n**Summary:**\n${data.summary}\n\n*You can now ask me questions about this document!*`;
    
    bubble.innerHTML = formatText(mdSummary);
    conversationHistory.push({ role: 'assistant', content: mdSummary });
    saveCurrentChat(conversationHistory);

  } catch (err) {
    bubble.innerHTML = `Error: ${err.message}`;
    removeChatAttachment();
  }
}

function removeChatAttachment() {
  const input = document.getElementById('chat-file-input');
  input.value = '';
  document.getElementById('chat-attachment-preview').style.display = 'none';
  hasActiveDocument = false;
}