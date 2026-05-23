import { loadData } from './data.js';
import { setState, subscribe, getState } from './state.js';
import { loadProfile } from './storage.js';
import { setupRouter, goto } from './router.js';
import { renderMap } from './views/map.js';
import { renderStage } from './views/stage.js';
import { renderCodex } from './views/codex.js';
import { updateProgress } from './views/components.js';

const mainEl = document.getElementById('appMain');

async function init() {
  try {
    const data = await loadData();
    setState({ data });
    document.body.dataset.theme = 'bamboo';
    setupRouter();
    subscribe(state => renderRoute(state));
    updateProgress();
    const profile = loadProfile();
    if (!profile.onboardingSeen) {
      const { showOnboarding } = await import('./views/onboarding.js');
      showOnboarding(() => renderRoute(getState()));
    } else {
      renderRoute(getState());
    }
  } catch (e) {
    console.error('init failed', e);
    mainEl.innerHTML = `<p style="color:#EF4444;">資料載入失敗：${e.message}</p>`;
  }
}

function renderRoute(state) {
  switch (state.route) {
    case 'map': renderMap(mainEl); break;
    case 'stage': renderStage(mainEl); break;
    case 'codex': renderCodex(mainEl); break;
  }
}

init();
