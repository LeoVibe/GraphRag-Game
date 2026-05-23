import { loadData, resolveCharacterId } from './data.js?v=2';
import { FONT_KEY, applyFont, bindSettingsEvents } from './settings.js';
import { applyHashToState, state, syncHash } from './state.js';
import { renderBattle } from './views/battle.js';
import { renderPerson } from './views/person.js';
import { renderRelation } from './views/relation.js';

// 統一配色：三 mode 用同一個視覺主題（classic 馬卡龍橘），不再 mode-by-mode 換色
// 之前 bamboo / warroom / classic 隨 mode 換的設計造成「不同 mode 像不同產品」，
// 視覺一致性差。改回單一主題後三 mode 共用同套色票、字體、卡片質感。
const UNIFIED_THEME = 'classic';
const MODE_LABEL = { person: '人物探險', battle: '戰役推理', relation: '關係路徑' };

const app = document.getElementById('app');
const loadState = document.getElementById('loadState');
const renderContext = { state };

init().catch(error => {
  console.error(error);
  document.body.dataset.theme = 'classic';
  loadState.textContent = `資料載入失敗：${error.message}`;
});

async function init() {
  await loadData();
  applyFont(localStorage.getItem(FONT_KEY) || 'medium');
  applyHashToState();
  syncHash(true);
  bindGlobalEvents();
  loadState.hidden = true;
  app.hidden = false;
  render();

  // 首次進站顯示 onboarding（3 步引導，可跳過、看過後不再顯示）
  const { hasSeenOnboarding, showOnboarding } = await import('./onboarding.js');
  if (!hasSeenOnboarding()) {
    showOnboarding();
  }
}

function bindGlobalEvents() {
  document.querySelector('.mode-tabs').addEventListener('click', event => {
    const button = event.target.closest('[data-mode-tab]');
    if (!button) return;
    setMode(button.dataset.modeTab);
  });
  bindSettingsEvents();
  app.addEventListener('click', handleAppClick);
  app.addEventListener('input', handleAppInput);
  window.addEventListener('popstate', () => {
    applyHashToState();
    render();
  });
  window.addEventListener('hashchange', () => {
    applyHashToState();
    render();
  });
}

function setMode(mode) {
  state.mode = mode;
  state.personTab = 'friends';
  state.relationFilter = '全部';
  state.reasoningStep = 'cause';
  state.relationTab = 'segments';
  syncHash();
  render();
}

function handleAppClick(event) {
  const button = event.target.closest('[data-action]');
  if (!button) return;
  const action = button.dataset.action;
  if (action === 'select-person') {
    state.personId = button.dataset.id;
    state.mode = 'person';
    state.personTab = 'friends';
    syncHash();
    render();
    return;
  }
  if (action === 'camp-filter') {
    state.campFilter = button.dataset.value;
    render();
    return;
  }
  if (action === 'person-tab') {
    state.personTab = button.dataset.value;
    render();
    return;
  }
  if (action === 'relation-filter') {
    state.relationFilter = button.dataset.value;
    render();
    return;
  }
  if (action === 'select-battle') {
    state.battleKey = button.dataset.key;
    state.mode = 'battle';
    state.reasoningStep = 'cause';
    syncHash();
    render();
    return;
  }
  if (action === 'reasoning-step') {
    state.reasoningStep = button.dataset.value;
    render();
    return;
  }
  if (action === 'relation-tab') {
    state.relationTab = button.dataset.value;
    render();
    return;
  }
  if (action === 'preset-pair') {
    state.fromId = resolveCharacterId(button.dataset.from);
    state.toId = resolveCharacterId(button.dataset.to);
    state.mode = 'relation';
    state.relationTab = 'segments';
    syncHash();
    render();
    return;
  }
  if (action === 'swap') {
    [state.fromId, state.toId] = [state.toId, state.fromId];
    syncHash();
    render();
    return;
  }
  if (action === 'clear-from') {
    state.fromId = '';
    syncHash();
    render();
    return;
  }
  if (action === 'clear-to') {
    state.toId = '';
    syncHash();
    render();
    return;
  }
  if (action === 'ep-edit') {
    // 開啟 inline 選人器
    const role = button.dataset.role;
    const block = button.closest('.endpoint-block');
    const picker = block?.querySelector('.ep-picker');
    if (picker) {
      picker.hidden = !picker.hidden;
      if (!picker.hidden) picker.querySelector('input')?.focus();
    }
    return;
  }
  if (action === 'ep-pick') {
    // 從建議清單選一個人物 → 填進對應 endpoint
    const role = button.dataset.role;
    const id = button.dataset.id;
    if (role === 'from') state.fromId = id;
    if (role === 'to') state.toId = id;
    syncHash();
    render();
  }
}

function handleAppInput(event) {
  if (event.target.matches('[data-person-search]')) {
    state.personSearch = event.target.value;
    render();
  }
  if (event.target.matches('[data-battle-search]')) {
    state.battleSearch = event.target.value;
    render();
  }
  if (event.target.matches('[data-ep-search]')) {
    // inline 選人器搜尋 — 不 re-render 整頁，只 update 建議清單
    const role = event.target.dataset.epSearch;
    const block = event.target.closest('.endpoint-block');
    const list = block?.querySelector(`[data-suggestions="${role}"]`);
    if (list) {
      import('./views/relation.js').then(m => {
        if (m.refreshSuggestions) m.refreshSuggestions(list, role, event.target.value);
      });
    }
  }
}

function render() {
  document.body.dataset.theme = UNIFIED_THEME;
  document.querySelectorAll('[data-mode-tab]').forEach(button => {
    button.classList.toggle('is-active', button.dataset.modeTab === state.mode);
  });
  if (state.mode === 'person') {
    renderPerson(app, renderContext);
    return;
  }
  if (state.mode === 'battle') {
    renderBattle(app, renderContext);
    return;
  }
  renderRelation(app, renderContext);
}
