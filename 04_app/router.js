import { getState, setState } from './state.js';

const ROUTE_TO_THEME = { map: 'bamboo', stage: 'warroom', codex: 'classic' };

export function setupRouter() {
  // 監聽 view-tabs button
  document.querySelectorAll('[data-route]').forEach(btn => {
    btn.addEventListener('click', () => {
      const route = btn.dataset.route;
      if (btn.disabled) return;
      goto(route);
    });
  });
}

export function goto(route) {
  setState({ route, verdictOpen: null });
  document.body.dataset.view = route;
  document.body.dataset.theme = ROUTE_TO_THEME[route] || 'classic';
  document.querySelectorAll('[data-route]').forEach(btn => {
    btn.classList.toggle('is-active', btn.dataset.route === route);
  });
}

export function setStageEnabled(enabled) {
  const tab = document.querySelector('[data-route="stage"]');
  if (tab) tab.disabled = !enabled;
}
