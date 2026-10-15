// Light / dark theme toggle. The saved choice is applied early by an inline script in each page head.
const KEY = 'ielts-theme';
const root = document.documentElement;
const icons = {
  moon: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>',
  sun: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
};
const systemDark = matchMedia('(prefers-color-scheme: dark)');

function current() { return root.dataset.theme || (systemDark.matches ? 'dark' : 'light'); }

function paint(button) {
  const dark = current() === 'dark';
  if (button.dataset.mode === current()) return; // avoid re-triggering the MutationObserver
  button.dataset.mode = current();
  if (button.classList.contains('theme-switch')) { // sidebar switch: static label, state in aria-checked
    button.setAttribute('aria-checked', String(dark));
    return;
  }
  button.innerHTML = dark ? icons.sun : icons.moon;
  button.setAttribute('aria-label', dark ? '切换到浅色模式' : '切换到深色模式');
  button.title = dark ? '浅色模式' : '深色模式';
}

function mount() {
  for (const header of document.querySelectorAll('.practice-header')) {
    if (header.querySelector('[data-theme-toggle]')) continue;
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'theme-toggle'; button.dataset.themeToggle = '';
    header.append(button);
  }
  document.querySelectorAll('[data-theme-toggle]').forEach(paint);
  // Keep the active link visible in the scrollable mobile nav.
  const nav = document.querySelector('.studio-nav nav'), active = nav?.querySelector('[aria-current]');
  if (nav && active && nav.scrollWidth > nav.clientWidth && !nav.dataset.scrolled) {
    nav.dataset.scrolled = '1';
    nav.scrollLeft = active.offsetLeft - (nav.clientWidth - active.offsetWidth) / 2;
  }
}

document.addEventListener('click', event => {
  if (!event.target.closest('[data-theme-toggle]')) return;
  const next = current() === 'dark' ? 'light' : 'dark';
  root.dataset.theme = next;
  try { localStorage.setItem(KEY, next); } catch {}
  document.querySelectorAll('[data-theme-toggle]').forEach(paint);
});
systemDark.addEventListener('change', () => document.querySelectorAll('[data-theme-toggle]').forEach(paint));
new MutationObserver(mount).observe(document.body, { childList: true, subtree: true });
mount();
