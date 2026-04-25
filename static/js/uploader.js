let uploadedFile = null;
let documentContent = null;
let lastDocQuestion = '';
let lastDocAnswer = '';

function openUploader() {
  document.getElementById('upload-panel').classList.add('open');
}

function closeUploader() {
  document.getElementById('upload-panel').classList.remove('open');
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const icons = {
    pdf: '📄', py: '🐍', ipynb: '📓', xlsx: '📊',
    csv: '📊', docx: '📝', txt: '📃', md: '📃',
    js: '📜', html: '🌐', json: '🔧', default: '📁'
  };
  return icons[ext] || icons.default;
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function initDropZone() {
  const zone = document.getElementById('drop-zone');
  const input = document.getElementById('file-input');

  zone.addEventListener('click', () => input.click());

  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));

  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) setFile(file);
  });

  input.addEventListener('change', () => {
    if (input.files[0]) setFile(input.files[0]);
  });
}

function setFile(file) {
  uploadedFile = file;
  const info = document.getElementById('upload-file-info');
  document.getElementById('file-icon-display').textContent = getFileIcon(file.name);
  document.getElementById('file-name-display').textContent = file.name;
  document.getElementById('file-size-display').textContent = formatSize(file.size);
  info.style.display = 'flex';
  document.getElementById('upload-summary').style.display = 'none';
  document.getElementById('doc-qa-section').style.display = 'none';
}

function removeFile() {
  uploadedFile = null;
  document.getElementById('upload-file-info').style.display = 'none';
  document.getElementById('file-input').value = '';
  document.getElementById('upload-summary').style.display = 'none';
  document.getElementById('doc-qa-section').style.display = 'none';
}

async function submitUpload() {
  if (!uploadedFile) return;

  const btn = document.getElementById('upload-submit-btn');
  const summaryBox = document.getElementById('upload-summary');
  const summaryContent = document.getElementById('summary-content');
  const qaSection = document.getElementById('doc-qa-section');

  btn.disabled = true;
  btn.textContent = 'Processing...';
  summaryBox.style.display = 'block';
  summaryContent.textContent = 'Analyzing your document...';
  qaSection.style.display = 'none';

  try {
    const formData = new FormData();
    formData.append('file', uploadedFile);

    const res = await fetch('/upload', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    if (!res.ok) {
      summaryContent.textContent = data.error || 'Upload failed.';
      return;
    }

    documentContent = data;
    summaryContent.innerHTML = formatText(
      typeof data.summary === 'string' ? data.summary : data.summary
    );

    qaSection.style.display = 'block';

    const suggestedDiv = document.getElementById('suggested-questions');
    suggestedDiv.innerHTML = '';
    const questions = extractSuggestedQuestions(
      typeof data.summary === 'string' ? data.summary : JSON.stringify(data.summary)
    );
    questions.forEach(q => {
      const chip = document.createElement('span');
      chip.className = 'suggested-q';
      chip.textContent = q;
      chip.onclick = () => askAboutDocument(q);
      suggestedDiv.appendChild(chip);
    });

  } catch (err) {
    summaryContent.textContent = 'Connection error. Please try again.';
  } finally {
    btn.disabled = false;
    btn.textContent = '📤 Upload & Analyze';
  }
}

function extractSuggestedQuestions(text) {
  const lines = text.split('\n');
  const questions = [];
  let inQuestions = false;

  for (const line of lines) {
    if (line.includes('SUGGESTED QUESTIONS') || line.includes('Suggested Questions')) {
      inQuestions = true;
      continue;
    }
    if (inQuestions && line.trim().startsWith('-')) {
      const q = line.replace(/^[-•*]\s*/, '').trim();
      if (q.length > 5) questions.push(q);
    }
    if (questions.length >= 3) break;
  }

  return questions.length > 0 ? questions : [
    'Can you summarize the main points?',
    'What are the key concepts here?',
    'Explain this in simple terms'
  ];
}

async function askAboutDocument(question) {
  if (!question) {
    question = document.getElementById('doc-qa-input').value.trim();
  }
  if (!question) return;

  document.getElementById('doc-qa-input').value = question;
  const btn = document.getElementById('doc-qa-btn');
  const answerBox = document.getElementById('doc-qa-answer');

  btn.disabled = true;
  btn.textContent = 'Thinking...';
  answerBox.style.display = 'block';
  answerBox.textContent = 'Analyzing document...';

  try {
    const res = await fetch('/ask-document', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question })
    });

    if (!res.ok) {
      const err = await res.json();
      answerBox.textContent = err.error || 'Something went wrong.';
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let buffer = '';

    answerBox.textContent = '';

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
              answerBox.innerHTML = formatText(fullText);
            }
          } catch(e) {}
        }
      }
    }

    lastDocQuestion = question;
    lastDocAnswer = fullText;

    answerBox.innerHTML += `
      <div style="margin-top: 15px; text-align: right;">
        <button onclick="continueInChat()" style="background: var(--accent); color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px;">
          💬 Continue in Chat
        </button>
      </div>
    `;

  } catch (err) {
    answerBox.textContent = 'Connection error. Please try again.';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Ask';
  }
}

function continueInChat() {
  if (!lastDocQuestion || !lastDocAnswer) return;
  
  // Add user question
  conversationHistory.push({ role: 'user', content: lastDocQuestion });
  addMessage('user', lastDocQuestion);
  
  // Add bot answer
  conversationHistory.push({ role: 'assistant', content: lastDocAnswer });
  const bubble = addMessage('bot', '');
  bubble.innerHTML = formatText(lastDocAnswer);
  if (typeof enhanceCodeBlocks === 'function') enhanceCodeBlocks(bubble);
  
  saveCurrentChat(conversationHistory);
  closeUploader();
  scrollBottom();
}

document.addEventListener('DOMContentLoaded', initDropZone);
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeUploader();
});