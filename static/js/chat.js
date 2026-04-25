let conversationHistory = [];
let isStreaming = false;
let activeDocuments = []; // Array of { id, name }

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
    const isDocQa = activeDocuments.length > 0;
    const endpoint = isDocQa ? '/ask-document' : '/ask';

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        question,
        document_ids: activeDocuments.map(d => d.id),
        history: isDocQa ? [] : conversationHistory.slice(-Config.MAX_HISTORY * 2)
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

  const formData = new FormData();
  formData.append('file', file);

  const bubble = addMessage('bot', '');
  bubble.innerHTML = '<span class="output-loading">Adding document to Knowledge Base...</span>';
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
    
    // Add to active documents state
    activeDocuments.push({ id: data.document_id, name: data.filename });
    renderDocumentChips();

    const mdSummary = `✅ **Document Added:** \`${data.filename}\`\n\n*This document is now in your Knowledge Base. You can upload more documents or ask questions about them!*`;
    
    bubble.innerHTML = formatText(mdSummary);
    conversationHistory.push({ role: 'assistant', content: mdSummary });
    saveCurrentChat(conversationHistory);

  } catch (err) {
    bubble.innerHTML = `Error: ${err.message}`;
    input.value = '';
  }
}

function renderDocumentChips() {
  const container = document.getElementById('knowledge-base-list');
  const emptyState = document.getElementById('kb-empty-state');
  
  // Remove existing chips
  const existingChips = container.querySelectorAll('.kb-chip');
  existingChips.forEach(c => c.remove());
  
  if (activeDocuments.length === 0) {
    if (emptyState) emptyState.style.display = 'block';
  } else {
    if (emptyState) emptyState.style.display = 'none';
    
    activeDocuments.forEach(doc => {
      const chip = document.createElement('div');
      chip.className = 'kb-chip';
      chip.style = "display: flex; align-items: center; justify-content: space-between; background: rgba(5, 150, 105, 0.05); border: 1px solid rgba(5, 150, 105, 0.2); padding: 8px 12px; border-radius: 8px; font-size: 13px; color: var(--text); transition: all 0.2s;";
      chip.onmouseover = () => chip.style.background = 'rgba(5, 150, 105, 0.15)';
      chip.onmouseout = () => chip.style.background = 'rgba(5, 150, 105, 0.05)';
      
      chip.innerHTML = `
        <div style="display: flex; align-items: center; overflow: hidden;">
          <span style="margin-right: 8px; font-size: 16px;">📄</span>
          <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${doc.name}">${doc.name}</span>
        </div>
        <button onclick="removeChatAttachment('${doc.id}')" style="background: none; border: none; color: #888; cursor: pointer; padding: 4px; margin-left: 8px; border-radius: 4px; display: flex; align-items: center; justify-content: center; transition: all 0.2s;" onmouseover="this.style.color='#ef4444'; this.style.background='rgba(239, 68, 68, 0.1)';" onmouseout="this.style.color='#888'; this.style.background='none';">✕</button>
      `;
      container.appendChild(chip);
    });
  }
}

function removeChatAttachment(docId) {
  activeDocuments = activeDocuments.filter(d => d.id !== docId);
  renderDocumentChips();
  // Clear the input so the same file can be uploaded again if needed
  document.getElementById('chat-file-input').value = '';
}