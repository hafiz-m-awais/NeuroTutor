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
  const code = pre.textContent.trim();

  btn.textContent = '⏳ Running...';
  btn.disabled = true;
  output.style.display = 'block';
  output.innerHTML = '<span class="output-loading">Loading Python environment...</span>';

  try {
    if (!window.pyodide) {
      output.innerHTML = '<span class="output-loading">First time setup — loading Pyodide (10-15 seconds)...</span>';
      window.pyodide = await loadPyodide();
    }

    output.innerHTML = '<span class="output-loading">Running...</span>';

    const result = await window.pyodide.runPythonAsync(`
import sys
import io
import traceback

_stdout = io.StringIO()
_stderr = io.StringIO()

sys.stdout = _stdout
sys.stderr = _stderr

try:
    exec("""${code.replace(/\\/g, '\\\\').replace(/"""/g, '\\"\\"\\"').replace(/`/g, '\\`')}""")
    _out = _stdout.getvalue()
    _err = _stderr.getvalue()
    result = _out if _out else '(code ran with no output)'
    if _err:
        result += '\\nWarnings: ' + _err
except Exception as e:
    result = 'Error: ' + traceback.format_exc()
finally:
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

result
`);

    output.innerHTML = `<span class="output-success">Output:</span>\n${escapeOutput(String(result))}`;

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