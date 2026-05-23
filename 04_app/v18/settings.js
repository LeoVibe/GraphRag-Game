export const FONT_KEY = 'sanguo-v18-font';

export function bindSettingsEvents() {
  document.querySelector('.font-scale').addEventListener('click', event => {
    const button = event.target.closest('[data-font]');
    if (!button) return;
    applyFont(button.dataset.font);
  });
  const settingsBtn = document.getElementById('settingsBtn');
  const settingsPopover = document.getElementById('settingsPopover');
  if (settingsBtn && settingsPopover) {
    settingsBtn.addEventListener('click', event => {
      event.stopPropagation();
      const isOpen = !settingsPopover.hidden;
      settingsPopover.hidden = isOpen;
      settingsBtn.setAttribute('aria-expanded', String(!isOpen));
    });
    document.addEventListener('click', event => {
      if (settingsPopover.hidden) return;
      if (settingsPopover.contains(event.target) || event.target === settingsBtn) return;
      settingsPopover.hidden = true;
      settingsBtn.setAttribute('aria-expanded', 'false');
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !settingsPopover.hidden) {
        settingsPopover.hidden = true;
        settingsBtn.setAttribute('aria-expanded', 'false');
        settingsBtn.focus();
      }
    });
  }
}

export function applyFont(font) {
  const next = ['small', 'medium', 'large'].includes(font) ? font : 'medium';
  document.body.dataset.font = next;
  localStorage.setItem(FONT_KEY, next);
  document.querySelectorAll('[data-font]').forEach(button => {
    button.classList.toggle('is-active', button.dataset.font === next);
  });
}
