'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const code = fs.readFileSync(__dirname + '/../docs/theme.js', 'utf8');
const KEY = 'germany-job-monitor:theme:v1';

function fixture(saved, storageBlocked = false) {
  const values = new Map();
  if (saved) values.set(KEY, saved);
  const attrs = {};
  const listeners = {};
  const docListeners = {};
  const selectListeners = {};
  const root = {
    style: {},
    setAttribute(name, value) { attrs[name] = String(value); },
    removeAttribute(name) { delete attrs[name]; }
  };
  const select = {
    value: '',
    addEventListener(name, callback) { selectListeners[name] = callback; }
  };
  const document = {
    documentElement: root,
    readyState: 'loading',
    getElementById(id) { return id === 'themeMode' ? select : null; },
    addEventListener(name, callback) { docListeners[name] = callback; }
  };
  const localStorage = {
    getItem(key) { if (storageBlocked) throw Error('blocked'); return values.get(key) ?? null; },
    setItem(key, value) { if (storageBlocked) throw Error('blocked'); values.set(key, value); },
    removeItem(key) { if (storageBlocked) throw Error('blocked'); values.delete(key); }
  };
  const window = { addEventListener(name, callback) { listeners[name] = callback; } };
  vm.runInNewContext(code, {document, window, localStorage});
  assert.ok(docListeners.DOMContentLoaded, 'Theme selector must initialize');
  docListeners.DOMContentLoaded();
  return {
    attrs, root, select, values,
    change(mode) { select.value = mode; selectListeners.change(); },
    storage() { listeners.storage({key: KEY}); }
  };
}

{
  const f = fixture();
  assert.equal(f.attrs['data-theme'], undefined, 'System should be default');
  assert.equal(f.select.value, 'system');
  assert.equal(f.root.style.colorScheme, 'light dark');
  f.change('dark');
  assert.equal(f.attrs['data-theme'], 'dark');
  assert.equal(f.values.get(KEY), 'dark');
  f.change('light');
  assert.equal(f.attrs['data-theme'], 'light');
  assert.equal(f.values.get(KEY), 'light');
  f.change('system');
  assert.equal(f.attrs['data-theme'], undefined);
  assert.equal(f.root.style.colorScheme, 'light dark');
  assert.equal(f.values.has(KEY), false, 'System should not persist a redundant preference');
}
{
  const f = fixture('dark');
  assert.equal(f.attrs['data-theme'], 'dark', 'Save must apply on page load');
  assert.equal(f.select.value, 'dark');
  f.values.set(KEY, 'light');
  f.storage();
  assert.equal(f.attrs['data-theme'], 'light', 'Changes from another tab should apply');
}
{
  const f = fixture(null, true);
  f.change('dark');
  assert.equal(f.attrs['data-theme'], 'dark', 'Theme should work with disabled storage');
}
console.log('PASS: System default, manual override, persistence, cross-tab updates, blocked storage');
