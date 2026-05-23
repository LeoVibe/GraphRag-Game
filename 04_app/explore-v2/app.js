import { loadData, resolveCharacterId } from './data.js';
import { FONT_KEY, applyFont, bindSettingsEvents } from './settings.js';
import { applyHashToState, state, syncHash } from './state.js';
import { renderBattle } from './views/battle.js';
import { renderPerson } from './views/person.js';
import { renderRelation } from './views/relation.js';

const MODE_THEME = { person: 'bamboo', battle: 'warroom', relation: 'classic' };
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
  if (action === 'preset-pair') {
    state.fromId = resolveCharacterId(button.dataset.from);
    state.toId = resolveCharacterId(button.dataset.to);
    state.mode = 'relation';
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
}

function render() {
  document.body.dataset.theme = MODE_THEME[state.mode];
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
