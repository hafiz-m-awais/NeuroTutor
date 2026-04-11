const DARK_KEY = 'askai_dark_mode';

function initDarkMode() {
  const saved = localStorage.getItem(DARK_KEY);
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const isDark = saved ? saved === 'true' : prefersDark;
  setDarkMode(isDark);
}

function toggleDarkMode() {
  const isDark = document.body.classList.contains('dark');
  setDarkMode(!isDark);
}

function setDarkMode(dark) {
  document.body.classList.toggle('dark', dark);
  localStorage.setItem(DARK_KEY, dark);
  const btn = document.getElementById('dark-toggle');
  if (btn) btn.textContent = dark ? '☀️' : '🌙';
}

document.addEventListener('DOMContentLoaded', initDarkMode);