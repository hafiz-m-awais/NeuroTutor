const STORAGE_KEY = 'neurotutor_chats';
const MAX_CHATS = 50;

let currentChatId = null;

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function getAllChats() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function saveAllChats(chats) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch {
    console.warn('Storage full');
  }
}

function saveCurrentChat(messages, title) {
  if (!messages || messages.length === 0) return;

  const chats = getAllChats();
  const existing = chats.findIndex(c => c.id === currentChatId);

  const chatData = {
    id: currentChatId,
    title: title || generateTitle(messages),
    messages,
    updatedAt: Date.now()
  };

  if (existing >= 0) {
    chats[existing] = chatData;
  } else {
    chats.unshift(chatData);
    if (chats.length > MAX_CHATS) chats.pop();
  }

  saveAllChats(chats);
  renderChatList();
}

function updateChatTitle(chatId, title) {
  const chats = getAllChats();
  const existing = chats.findIndex(c => c.id === chatId);
  if (existing >= 0) {
    chats[existing].title = title;
    saveAllChats(chats);
    renderChatList();
  }
}

function generateTitle(messages) {
  const firstUser = messages.find(m => m.role === 'user');
  if (!firstUser) return 'New chat';
  const title = firstUser.content.slice(0, 40);
  return title.length < firstUser.content.length ? title + '...' : title;
}

function loadChat(chatId) {
  const chats = getAllChats();
  const chat = chats.find(c => c.id === chatId);
  if (!chat) return;

  currentChatId = chatId;
  conversationHistory = chat.messages;

  const chatEl = document.getElementById('chat');
  chatEl.innerHTML = '';

  chat.messages.forEach(msg => {
    const isUser = msg.role === 'user';
    const div = document.createElement('div');
    div.className = `msg ${isUser ? 'user' : 'bot'}`;
    div.innerHTML = `
      <div class="msg-avatar">${isUser ? 'U' : 'N'}</div>
      <div class="bubble">${isUser ? escapeHtml(msg.content) : formatText(msg.content)}</div>
    `;
    chatEl.appendChild(div);

    if (!isUser) {
      enhanceCodeBlocks(div.querySelector('.bubble'));
    }
  });

  chatEl.scrollTop = chatEl.scrollHeight;
  renderChatList();

  if (window.innerWidth < 768) {
    toggleSidebar();
  }
}

function deleteChat(chatId, event) {
  event.stopPropagation();
  if (!confirm('Delete this chat? This cannot be undone.')) return;

  const chats = getAllChats().filter(c => c.id !== chatId);
  saveAllChats(chats);

  if (currentChatId === chatId) {
    startNewChat();
  } else {
    renderChatList();
  }
}

function startNewChat() {
  currentChatId = generateId();
  conversationHistory = [];

  const chatEl = document.getElementById('chat');
  chatEl.innerHTML = `
    <div class="welcome" id="welcome">
      <div class="icon">N</div>
      <h2>Welcome to NeuroTutor!</h2>
      <p>I'm your AI tutor for Machine Learning and Data Science. Ask me anything!</p>
    </div>`;

  renderChatList();
  document.getElementById('input').focus();
}

function renderChatList() {
  const chats = getAllChats();
  const listEl = document.getElementById('chat-list');
  if (!listEl) return;

  if (chats.length === 0) {
    listEl.innerHTML = `
      <div class="empty-chats">
        No previous chats yet.<br>Start asking questions!
      </div>`;
    return;
  }

  listEl.innerHTML = chats.map(chat => `
    <div class="chat-item ${chat.id === currentChatId ? 'active' : ''}"
         onclick="loadChat('${chat.id}')">
      <div class="chat-item-text">
        <div class="chat-item-title">${escapeHtml(chat.title)}</div>
        <div class="chat-item-time">${timeAgo(chat.updatedAt)}</div>
      </div>
      <button class="chat-item-delete"
              onclick="deleteChat('${chat.id}', event)"
              title="Delete chat">×</button>
    </div>
  `).join('');
}

function timeAgo(timestamp) {
  const diff = Date.now() - timestamp;
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return new Date(timestamp).toLocaleDateString();
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('collapsed');
  const btn = document.getElementById('sidebar-toggle');
  btn.textContent = sidebar.classList.contains('collapsed') ? '☰' : '✕';
}

function showProgressDashboard() {
  const chats = getAllChats();
  const modal = document.getElementById('stats-modal');
  const body = document.getElementById('stats-body');
  
  if (!modal || !body) return;
  
  let totalQuestions = 0;
  let topics = new Set();
  let quizScores = [];
  let docsAnalyzed = 0;
  
  chats.forEach(chat => {
    if (chat.title && chat.title !== 'New chat') {
      topics.add(chat.title);
    }
    
    chat.messages.forEach(msg => {
      if (msg.role === 'user') {
        totalQuestions++;
        if (msg.content.includes('Please summarize the document:')) {
          docsAnalyzed++;
        }
      }
      
      // Check for quiz scores injected into chat
      if (msg.role === 'assistant' && msg.content.includes('You scored')) {
        const match = msg.content.match(/You scored (\d+)\/(\d+)/);
        if (match) {
          quizScores.push({ score: parseInt(match[1]), total: parseInt(match[2]) });
        }
      }
    });
  });
  
  const avgQuizScore = quizScores.length > 0 
    ? (quizScores.reduce((acc, q) => acc + (q.score / q.total), 0) / quizScores.length * 100).toFixed(0)
    : 0;

  body.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
      <div style="background: var(--bg); padding: 16px; border-radius: 12px; border: 1px solid var(--border); text-align: center;">
        <div style="font-size: 24px; font-weight: 800; color: var(--accent);">${totalQuestions}</div>
        <div style="font-size: 12px; color: var(--subtext); text-transform: uppercase; margin-top: 4px;">Questions Asked</div>
      </div>
      <div style="background: var(--bg); padding: 16px; border-radius: 12px; border: 1px solid var(--border); text-align: center;">
        <div style="font-size: 24px; font-weight: 800; color: var(--accent);">${topics.size}</div>
        <div style="font-size: 12px; color: var(--subtext); text-transform: uppercase; margin-top: 4px;">Topics Studied</div>
      </div>
      <div style="background: var(--bg); padding: 16px; border-radius: 12px; border: 1px solid var(--border); text-align: center;">
        <div style="font-size: 24px; font-weight: 800; color: var(--accent);">${docsAnalyzed}</div>
        <div style="font-size: 12px; color: var(--subtext); text-transform: uppercase; margin-top: 4px;">Docs Analyzed</div>
      </div>
      <div style="background: var(--bg); padding: 16px; border-radius: 12px; border: 1px solid var(--border); text-align: center;">
        <div style="font-size: 24px; font-weight: 800; color: var(--accent);">${avgQuizScore}%</div>
        <div style="font-size: 12px; color: var(--subtext); text-transform: uppercase; margin-top: 4px;">Avg Quiz Score</div>
      </div>
    </div>
    
    <div class="debug-label">Study Topics</div>
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px;">
      ${Array.from(topics).slice(0, 10).map(t => `<span class="chip" style="margin: 0; cursor: default;">${escapeHtml(t)}</span>`).join('')}
      ${topics.size === 0 ? '<div style="font-size: 13px; color: var(--subtext); font-style: italic;">No topics yet. Start chatting!</div>' : ''}
    </div>
    
    <div class="debug-label">Quiz History</div>
    <div style="font-size: 13px; color: var(--subtext);">
      ${quizScores.length > 0 ? `You have completed ${quizScores.length} quizzes. Keep up the good work!` : 'No quizzes completed yet.'}
    </div>
  `;
  
  modal.classList.add('open');
}

document.addEventListener('DOMContentLoaded', () => {
  currentChatId = generateId();
  renderChatList();

  // Mobile Swipe Gestures
  let touchStartX = 0;
  let touchEndX = 0;
  
  window.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });
  
  window.addEventListener('touchend', e => {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
  }, { passive: true });
  
  function handleSwipe() {
    const sidebar = document.getElementById('sidebar');
    const swipeDistance = touchEndX - touchStartX;
    const threshold = 100;
    
    // Swipe Right (from left edge) -> Open
    if (swipeDistance > threshold && touchStartX < 50) {
      if (sidebar.classList.contains('collapsed')) {
        toggleSidebar();
      }
    }
    
    // Swipe Left -> Close
    if (swipeDistance < -threshold) {
      if (!sidebar.classList.contains('collapsed')) {
        toggleSidebar();
      }
    }
  }
});