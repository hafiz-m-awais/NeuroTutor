let fixedCode = '';

function openDebugger() {
  document.getElementById('debug-panel').classList.add('open');
  document.getElementById('debug-input').focus();
}

function closeDebugger() {
  document.getElementById('debug-panel').classList.remove('open');
}

function clearDebugger() {
  document.getElementById('debug-input').value = '';
  document.getElementById('debug-result').style.display = 'none';
  document.getElementById('debug-run-fixed').style.display = 'none';
  fixedCode = '';
}

function extractFixedCode(text) {
  const match = text.match(/```python\n?([\s\S]*?)```/);
  return match ? match[1].trim() : '';
}

async function submitDebug() {
  const code = document.getElementById('debug-input').value.trim();
  if (!code) return;

  const btn = document.getElementById('debug-submit');
  const resultBox = document.getElementById('debug-result');
  const resultContent = document.getElementById('debug-result-content');
  const runFixedBtn = document.getElementById('debug-run-fixed');

  btn.disabled = true;
  btn.textContent = 'Analyzing...';
  resultBox.style.display = 'block';
  resultContent.textContent = 'AI is analyzing your code...';
  runFixedBtn.style.display = 'none';
  fixedCode = '';

  try {
    const res = await fetch('/debug', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });

    if (!res.ok) {
      const err = await res.json();
      resultContent.textContent = err.error || 'Something went wrong.';
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    let buffer = '';

    resultContent.textContent = '';

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
              resultContent.innerHTML = formatText(fullText);
              enhanceCodeBlocks(resultContent);
            }
          } catch(e) {}
        }
      }
    }

    fixedCode = extractFixedCode(fullText);
    if (fixedCode) {
      runFixedBtn.style.display = 'block';
    }

  } catch (err) {
    resultContent.textContent = 'Connection error. Please try again.';
  } finally {
    btn.disabled = false;
    btn.textContent = 'Find & Fix Bug';
  }
}

function runFixedCode() {
  if (!fixedCode) return;
  closeDebugger();
  const question = `I fixed my code. Can you explain this fixed version and run it?\n\`\`\`python\n${fixedCode}\n\`\`\``;
  document.getElementById('input').value = question;
  sendMessage();
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeDebugger();
});