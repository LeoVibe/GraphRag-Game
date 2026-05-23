// 全域應用狀態 + custom event broadcast
const STATE_KEY_DEFAULT = {
  data: null,                          // { nodes, rels, personality }
  route: 'map',                        // 'map' | 'stage' | 'codex'
  currentPackId: null,                 // active 任務舞台所在事件包
  currentQuestion: null,               // { type, subject, edge, choices, ... }
  selectedChoice: null,                // 暫存選項
  questionsAnswered: 0,                // 本次任務舞台已答題數
  questionsTarget: 5,                  // 每個事件包要答幾題才算過關
  verdictOpen: null,                   // null | { correct, explanation, newLevel, ... }
};

let state = { ...STATE_KEY_DEFAULT };
const listeners = new Set();

export function getState() { return state; }
export function setState(partial) {
  state = { ...state, ...partial };
  broadcast();
}
export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function broadcast() {
  for (const fn of listeners) fn(state);
}
