let quizData = null;
let answers = [];
let currentTopic = '';

function openQuiz(topic) {
  document.getElementById('quiz-panel').classList.add('open');
  if (topic) {
    document.getElementById('quiz-topic-input').value = topic;
    generateQuiz(topic);
  } else {
    document.getElementById('quiz-topic-input').focus();
  }
}

function closeQuiz() {
  document.getElementById('quiz-panel').classList.remove('open');
}

function setQuizTopic(topic) {
  document.getElementById('quiz-topic-input').value = topic;
  generateQuiz(topic);
}

async function generateQuiz(topic) {
  if (!topic) topic = document.getElementById('quiz-topic-input').value.trim();
  if (!topic) return;

  const count = parseInt(document.getElementById('quiz-count').value) || 3;
  currentTopic = topic;
  quizData = null;
  answers = [];

  const body = document.getElementById('quiz-body-content');
  const btn = document.getElementById('quiz-generate-btn');
  const header = document.getElementById('quiz-header-topic');

  btn.disabled = true;
  btn.textContent = 'Generating...';
  header.textContent = topic;
  body.innerHTML = `<div class="quiz-loading">Generating quiz on "${topic}"...<br><br>Please wait a moment.</div>`;

  // Check Cache
  const cacheKey = `quiz_cache_${topic.toLowerCase()}_${count}`;
  const cached = sessionStorage.getItem(cacheKey);
  if (cached) {
    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp < 600000) { // 10 minutes
      console.info(`Loading quiz for ${topic} from cache`);
      quizData = data;
      renderQuiz();
      btn.disabled = false;
      btn.textContent = 'Generate';
      return;
    }
  }

  try {
    const res = await fetch('/quiz', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ topic, count })
    });

    const data = await res.json();

    if (!res.ok) {
      if (data.error && data.error.includes("providers are busy")) {
        let timeLeft = 60;
        body.innerHTML = `
          <div class="quiz-loading" style="color:#f9a826;">
            <div style="font-size: 24px; margin-bottom: 12px;">⏳</div>
            All AI providers are currently busy.<br>
            Please wait <strong id="quota-timer">${timeLeft}</strong> seconds and try again.
          </div>
        `;
        const timerInterval = setInterval(() => {
          timeLeft--;
          const timerEl = document.getElementById('quota-timer');
          if (timerEl) timerEl.textContent = timeLeft;
          if (timeLeft <= 0) {
            clearInterval(timerInterval);
            if (timerEl) {
              body.innerHTML = `<div class="quiz-loading" style="color:#4caf50;">Ready to try again! Click Generate.</div>`;
              btn.disabled = false;
            }
          }
        }, 1000);
        return; // Exit and let timer re-enable button
      } else {
        body.innerHTML = `<div class="quiz-loading" style="color:#f44336">${data.error || 'Failed to generate quiz'}</div>`;
        return;
      }
    }

    quizData = data;
    sessionStorage.setItem(cacheKey, JSON.stringify({ data, timestamp: Date.now() }));
    renderQuiz();

  } catch (err) {
    body.innerHTML = `<div class="quiz-loading" style="color:#f44336">Connection error. Please try again.</div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate';
  }
}

function renderQuiz() {
  if (!quizData) return;

  const body = document.getElementById('quiz-body-content');
  answers = new Array(quizData.questions.length).fill(null);

  const dotsHtml = quizData.questions.map((_, i) =>
    `<div class="progress-dot" id="dot-${i}"></div>`
  ).join('');

  const questionsHtml = quizData.questions.map((q, qi) => `
    <div class="question-card" id="qcard-${qi}">
      <div class="question-num">Question ${qi + 1} of ${quizData.questions.length}</div>
      <div class="question-text">${escapeHtml(q.question)}</div>
      <div class="options">
        ${q.options.map((opt, oi) => `
          <button class="option" id="opt-${qi}-${oi}"
                  onclick="selectAnswer(${qi}, ${oi})">
            <strong>${['A', 'B', 'C', 'D'][oi]}.</strong> ${escapeHtml(opt)}
          </button>
        `).join('')}
      </div>
      <div class="explanation" id="exp-${qi}">
        ✅ ${escapeHtml(q.explanation)}
      </div>
    </div>
  `).join('');

  body.innerHTML = `
    <div class="progress-dots">${dotsHtml}</div>
    ${questionsHtml}
    <div class="quiz-score" id="quiz-score">
      <div class="score-circle">
        <div class="score-num" id="score-num">0</div>
        <div class="score-total">/ ${quizData.questions.length}</div>
      </div>
      <div class="score-msg" id="score-msg">Good effort!</div>
      <div class="score-sub" id="score-sub">Keep practicing to improve</div>
      <button class="quiz-retry-btn" onclick="generateQuiz('${escapeHtml(currentTopic)}')">
        Try Again
      </button>
    </div>
  `;
}

function selectAnswer(questionIndex, optionIndex) {
  if (answers[questionIndex] !== null) return;

  answers[questionIndex] = optionIndex;
  const q = quizData.questions[questionIndex];
  const isCorrect = optionIndex === q.correct;

  for (let i = 0; i < q.options.length; i++) {
    const btn = document.getElementById(`opt-${questionIndex}-${i}`);
    btn.disabled = true;
    if (i === q.correct) btn.classList.add('correct');
    else if (i === optionIndex && !isCorrect) btn.classList.add('wrong');
  }

  document.getElementById(`exp-${questionIndex}`).style.display = 'block';

  const dot = document.getElementById(`dot-${questionIndex}`);
  dot.classList.add('answered');
  dot.classList.add(isCorrect ? 'correct' : 'wrong');

  if (answers.every(a => a !== null)) {
    setTimeout(showScore, 800);
  }
}

function showScore() {
  const correct = answers.filter((a, i) => a === quizData.questions[i].correct).length;
  const total = quizData.questions.length;
  const pct = Math.round((correct / total) * 100);

  const scoreEl = document.getElementById('quiz-score');
  document.getElementById('score-num').textContent = correct;

  let msg, sub;
  if (pct === 100) { msg = 'Perfect score!'; sub = 'You nailed it. Try a harder topic!'; }
  else if (pct >= 67) { msg = 'Good job!'; sub = 'Review the ones you missed and try again.'; }
  else if (pct >= 33) { msg = 'Keep practicing!'; sub = 'Re-read the concept and try again.'; }
  else { msg = 'Need more practice'; sub = 'Ask AI to explain this topic again first.'; }

  document.getElementById('score-msg').textContent = msg;
  document.getElementById('score-sub').textContent = sub;
  scoreEl.style.display = 'block';
  scoreEl.scrollIntoView({ behavior: 'smooth' });

  // Fix 6: Inject quiz result into chat history so it's saved permanently
  const emoji = pct === 100 ? '🏆' : pct >= 67 ? '✅' : pct >= 33 ? '📖' : '💪';
  const chatMsg = `${emoji} **Quiz Complete — ${currentTopic}**\n\n**Score: ${correct}/${total} (${pct}%)**\n${msg}\n\n${sub}\n\n*Ask me to explain any topic you got wrong!*`;
  if (typeof conversationHistory !== 'undefined' && typeof saveCurrentChat !== 'undefined') {
    conversationHistory.push({ role: 'assistant', content: chatMsg });
    saveCurrentChat(conversationHistory);
  }
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeQuiz();
});