function enhanceCodeBlocks(bubble) {
  const pres = bubble.querySelectorAll('pre');
  pres.forEach((pre, index) => {
    if (pre.parentElement.classList.contains('code-block-wrapper')) return;

    const code = pre.querySelector('code');
    const language = detectLanguage(code ? code.textContent : pre.textContent);

    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';

    const header = document.createElement('div');
    header.className = 'code-header';
    header.innerHTML = `
      <span class="code-lang">${language}</span>
      <div class="code-actions">
        <button class="run-btn" onclick="runCode(this)" title="Run code">▶ Run</button>
        <button class="copy-btn" onclick="copyCode(this)" title="Copy code">Copy</button>
      </div>
    `;

    const outputDiv = document.createElement('div');
    outputDiv.className = 'code-output';
    outputDiv.style.display = 'none';

    wrapper.appendChild(header);
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    wrapper.appendChild(outputDiv);
  });
}

function detectLanguage(code) {
  if (code.includes('import torch') || code.includes('nn.Module')) return 'PyTorch';
  if (code.includes('import tensorflow') || code.includes('keras')) return 'TensorFlow';
  if (code.includes('import pandas') || code.includes('DataFrame')) return 'Python / Pandas';
  if (code.includes('import numpy') || code.includes('np.')) return 'Python / NumPy';
  if (code.includes('sklearn') || code.includes('fit(')) return 'Python / Sklearn';
  if (code.includes('def ') || code.includes('import ')) return 'Python';
  return 'Code';
}

function copyCode(btn) {
  const pre = btn.closest('.code-block-wrapper').querySelector('pre');
  const text = pre.textContent;
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

async function runCode(btn) {
  const wrapper = btn.closest('.code-block-wrapper');
  const pre = wrapper.querySelector('pre');
  const output = wrapper.querySelector('.code-output');
  const code = pre.textContent;

  btn.textContent = '⏳ Running...';
  btn.disabled = true;
  output.style.display = 'block';
  output.innerHTML = '<span class="output-loading">Loading Python...</span>';

  try {
    if (!window.pyodide) {
      output.innerHTML = '<span class="output-loading">Loading Pyodide (first time takes 10s)...</span>';
      await loadPyodideRuntime();
    }

    const result = await window.pyodide.runPythonAsync(`
import sys
import io
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
try:
    exec(${JSON.stringify(code)})
    output = sys.stdout.getvalue()
    error = sys.stderr.getvalue()
    output + ('\\nSTDERR: ' + error if error else '')
except Exception as e:
    sys.stdout.getvalue() + '\\nError: ' + str(e)
`);
    output.innerHTML = `<span class="output-success">Output:</span>\n${escapeOutput(result || '(no output)')}`;
  } catch (err) {
    output.innerHTML = `<span class="output-error">Error: ${escapeOutput(err.message)}</span>`;
  }

  btn.textContent = '▶ Run';
  btn.disabled = false;
}

async function loadPyodideRuntime() {
  return new Promise((resolve, reject) => {
    if (window.loadPyodide) {
      window.loadPyodide().then(py => {
        window.pyodide = py;
        resolve();
      });
    } else {
      reject(new Error('Pyodide not loaded'));
    }
  });
}

function escapeOutput(text) {
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}