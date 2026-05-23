import { BATTLES, getBattleByKey } from './battle-presets.js';
import { nodeName, resolveCharacterId } from './data.js';

export const DEFAULT_PERSON = 'entity:character_劉備';
export const DEFAULT_FROM = 'entity:character_關羽';
export const DEFAULT_TO = 'entity:character_周瑜';

export const state = {
  mode: 'person',
  personId: DEFAULT_PERSON,
  personTab: 'friends',
  relationFilter: '全部',
  personSearch: '',
  campFilter: 'all',
  battleKey: 'guandu',
  battleSearch: '',
  reasoningStep: 'cause',
  fromId: DEFAULT_FROM,
  toId: DEFAULT_TO,
  relationTab: 'segments'
};

export function setState(patch) {
  Object.assign(state, patch);
}

export function setStateValue(key, value) {
  state[key] = value;
}

export function currentBattle() {
  return getBattleByKey(state.battleKey);
}

export function applyHashToState() {
  const params = new URLSearchParams(location.hash.slice(1));
  const mode = params.get('mode');
  if (['person', 'battle', 'relation'].includes(mode)) state.mode = mode;
  if (state.mode === 'person') {
    state.personId = resolveCharacterId(params.get('subject')) || DEFAULT_PERSON;
  }
  if (state.mode === 'battle') {
    const subject = params.get('subject');
    const battle = BATTLES.find(item => item.key === subject || item.name === subject);
    state.battleKey = battle ? battle.key : 'guandu';
  }
  if (state.mode === 'relation') {
    const subject = params.get('subject');
    if (subject && subject.includes('→')) {
      const [from, to] = subject.split('→');
      state.fromId = resolveCharacterId(from.trim()) || DEFAULT_FROM;
      state.toId = resolveCharacterId(to.trim()) || DEFAULT_TO;
    } else {
      state.fromId = resolveCharacterId(params.get('from')) || DEFAULT_FROM;
      state.toId = resolveCharacterId(params.get('to')) || DEFAULT_TO;
    }
  }
}

export function syncHash(replace = false) {
  const params = new URLSearchParams();
  params.set('mode', state.mode);
  if (state.mode === 'person') params.set('subject', nodeName(state.personId));
  if (state.mode === 'battle') params.set('subject', currentBattle().name);
  if (state.mode === 'relation') {
    if (state.fromId) params.set('from', nodeName(state.fromId));
    if (state.toId) params.set('to', nodeName(state.toId));
  }
  const next = `#${params.toString()}`;
  if (location.hash === next) return;
  history[replace ? 'replaceState' : 'pushState'](null, '', next);
}
