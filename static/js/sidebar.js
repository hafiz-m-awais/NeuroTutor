const STORAGE_KEY = 'neurotutor_chats';
const MAX_CHATS = 50;

let currentChatId = null;
let cachedChats = [];

function generateId() {
  return 'chat_' + Date.now().toString(36) + Math.random().toString(36).slice(2);
}

// --- Cloud Sync Helpers ---

async function fetchAllChats() {
  try {
    const res = await fetch('/api/chats', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (res.ok) {
      cachedChats = await res.json();
      renderChatList();
    }
  } catch (err) {
    console.error('Failed to fetch chats from cloud', err);
  }
}

async function fetchChatDetails(chatId) {
  try {
    const res = await fetch(`/api/chats/${chatId}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
    if (res.ok) return await res.json();
  } catch (err) {
    console.error('Failed to fetch chat details', err);
  }
  return null;
}

async function uploadChat(chatData) {
  try {
    await fetch('/api/chats', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest' 
      },
      body: JSON.stringify(chatData)
    });
  } catch (err) {
    console.error('Failed to sync chat to cloud', err);
  }
}

async function removeChatFromServer(chatId) {
  try {
    await fetch(`/api/chats/${chatId}`, {
      method: 'DELETE',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    });
  } catch (err) {
    console.error('Failed to delete chat from cloud', err);
  }
}

// --- Migration logic ---
async function migrateLegacyChats() {
  const legacy = localStorage.getItem(STORAGE_KEY);
  if (!legacy) return;

  try {
    const chats = JSON.parse(legacy);
    if (chats.length > 0) {
      console.info(`Migrating ${chats.length} legacy chats to cloud...`);
      for (const chat of chats) {
        await uploadChat(chat);
      }
    }
    localStorage.removeItem(STORAGE_KEY);
    await fetchAllChats();
  } catch (e) {
    console.error('Migration failed', e);
  }
}

// --- Main Chat Logic ---

async function saveCurrentChat(messages, title) {
  if (!messages || messages.length === 0) return;

  const chatData = {
    id: currentChatId,
    title: title || generateTitle(messages),
    messages,
    updatedAt: Date.now()
  };

  // Optimistic UI update
  const idx = cachedChats.findIndex(c => c.id === currentChatId);
  if (idx >= 0) {
    cachedChats[idx] = { id: chatData.id, title: chatData.title, updatedAt: chatData.updatedAt };
  } else {
    cachedChats.unshift({ id: chatData.id, title: chatData.title, updatedAt: chatData.updatedAt });
  }
  renderChatList();

  // Sync to server
  await uploadChat(chatData);
}

async function updateChatTitle(chatId, title) {
  const chatData = await fetchChatDetails(chatId);
  if (chatData) {
    chatData.title = title;
    // Update local cache for UI
    const idx = cachedChats.findIndex(c => c.id === chatId);
    if (idx >= 0) cachedChats[idx].title = title;
    renderChatList();
    // Sync to server
    await uploadChat(chatData);
  }
}

function generateTitle(messages) {
  const firstUser = messages.find(m => m.role === 'user');
  if (!firstUser) return 'New chat';
  const title = firstUser.content.slice(0, 40);
  return title.length < firstUser.content.length ? title + '...' : title;
}

async function loadChat(chatId) {
  const chat = await fetchChatDetails(chatId);
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

async function deleteChat(chatId, event) {
  event.stopPropagation();
  if (!confirm('Delete this chat? This cannot be undone.')) return;

  // Optimistic UI update
  cachedChats = cachedChats.filter(c => c.id !== chatId);
  renderChatList();

  // Sync to server
  await removeChatFromServer(chatId);

  if (currentChatId === chatId) {
    startNewChat();
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
  const listEl = document.getElementById('chat-list');
  if (!listEl) return;

  if (cachedChats.length === 0) {
    listEl.innerHTML = `
      <div class="empty-chats">
        No previous chats yet.<br>Start asking questions!
      </div>`;
    return;
  }

  listEl.innerHTML = cachedChats.map(chat => `
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
  if (!sidebar) return;
  sidebar.classList.toggle('collapsed');
  const btn = document.getElementById('sidebar-toggle');
  if (btn) btn.textContent = sidebar.classList.contains('collapsed') ? '☰' : '✕';
}

async function showProgressDashboard() {
  const modal = document.getElementById('stats-modal');
  const body = document.getElementById('stats-body');
  if (!modal || !body) return;

  body.innerHTML = `<div class="quiz-loading">Calculating your progress...</div>`;
  modal.classList.add('open');

  let totalQuestions = 0;
  let topics = new Set();
  let quizScores = [];
  let docsAnalyzed = 0;

  // We need full details for stats, so we fetch each chat sequentially or in parallel
  const fullChats = await Promise.all(cachedChats.slice(0, 20).map(c => fetchChatDetails(c.id)));

  fullChats.forEach(chat => {
    if (!chat) return;
    if (chat.title && chat.title !== 'New chat') topics.add(chat.title);
    
    chat.messages.forEach(msg => {
      if (msg.role === 'user') {
        totalQuestions++;
        if (msg.content.includes('Please summarize the document:')) docsAnalyzed++;
      }
      if (msg.role === 'assistant' && msg.content.includes('You scored')) {
        const match = msg.content.match(/You scored (\d+)\/(\d+)/);
        if (match) quizScores.push({ score: parseInt(match[1]), total: parseInt(match[2]) });
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
}

document.addEventListener('DOMContentLoaded', async () => {
  currentChatId = generateId();
  
  // Initial Sync
  await migrateLegacyChats();
  await fetchAllChats();

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
    if (!sidebar) return;
    const swipeDistance = touchEndX - touchStartX;
    const threshold = 100;
    
    if (swipeDistance > threshold && touchStartX < 50) {
      if (sidebar.classList.contains('collapsed')) toggleSidebar();
    }
    if (swipeDistance < -threshold) {
      if (!sidebar.classList.contains('collapsed')) toggleSidebar();
    }
  }
});