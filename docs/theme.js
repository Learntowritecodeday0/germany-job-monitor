'use strict';
// Theme preference is independent of application history and never leaves this browser.
// CSS follows prefers-color-scheme whenever the preference is "system".
(() => {
  const KEY = 'germany-job-monitor:theme:v1';
  const MODES = new Set(['system', 'light', 'dark']);
  function load() {
    try {
      const saved = localStorage.getItem(KEY);
      return MODES.has(saved) ? saved : 'system';
    } catch (_) {
      return 'system';
    }
  }
  function apply(mode) {
    if (!MODES.has(mode)) mode = 'system';
    const root = document.documentElement;
    if (mode === 'system') {
      root.removeAttribute('data-theme');
      root.style.colorScheme = 'light dark';
    } else {
      root.setAttribute('data-theme', mode);
      root.style.colorScheme = mode;
    }
    const select = document.getElementById('themeMode');
    if (select) select.value = mode;
  }
  function init() {
    const control = document.getElementById('themeMode');
    if (!control) return;
    control.value = load();
    control.addEventListener('change', () => {
      const selected = MODES.has(control.value) ? control.value : 'system';
      apply(selected);
      try {
        if (selected === 'system') localStorage.removeItem(KEY);
        else localStorage.setItem(KEY, selected);
      } catch (_) {
        // Private mode / blocked storage: choice works until the page reloads.
      }
    });
  }
  apply(load()); // Runs before the stylesheet is loaded to avoid a theme flash.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
  window.addEventListener('storage', event => {
    if (event.key === KEY) apply(load());
  });
})();
