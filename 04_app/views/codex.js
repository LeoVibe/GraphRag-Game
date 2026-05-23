import { getState } from '../state.js';
import { loadProfile } from '../storage.js';

const CAMPS = [
  { id: 'all', label: '全部' },
  { id: 'wei', label: '曹魏' },
  { id: 'shu', label: '劉蜀' },
  { id: 'wu', label: '東吳' },
  { id: 'lords', label: '群雄' },
  { id: 'mixed', label: '混合' },
];

let activeCampFilter = 'all';

export function renderCodex(mainEl) {
  const { data } = getState();
  if (!data) {
    mainEl.innerHTML = '<p>資料載入中…</p>';
    return;
  }
  const profile = loadProfile();
  const allChars = data.nodes.filter(n => n.type === 'character' && n.isTrunk);
  const filtered = activeCampFilter === 'all' ? allChars
    : allChars.filter(n => n.camp === activeCampFilter);
  // 分組
  const groups = { 3: [], 2: [], 1: [], 0: [] };
  for (const n of filtered) {
    const level = profile.characters[n.id]?.level ?? 0;
    groups[level].push(n);
  }
  mainEl.innerHTML = `
    <div class="codex-filters" role="tablist" aria-label="陣營篩選">
      ${CAMPS.map(c => `<button class="chip ${c.id === activeCampFilter ? 'is-active' : ''}"
        data-camp="${c.id}">${c.label}</button>`).join('')}
    </div>
    <section class="codex-section">
      <h2>★★★ 熟識（${groups[3].length}）</h2>
      <div class="codex-grid">${groups[3].map(cardHtml).join('') || emptyHint('還沒熟識任何人')}</div>
    </section>
    <section class="codex-section">
      <h2>★★ 認識（${groups[2].length}）</h2>
      <div class="codex-grid">${groups[2].map(cardHtml).join('') || emptyHint('還沒')}</div>
    </section>
    <section class="codex-section">
      <h2>★ 聽過（${groups[1].length}）</h2>
      <div class="codex-grid">${groups[1].map(cardHtml).join('') || emptyHint('還沒')}</div>
    </section>
    <section class="codex-section">
      <h2>? 還沒遇見（${groups[0].length}）</h2>
      <div class="codex-grid">${groups[0].map(cardHtml).join('')}</div>
    </section>
  `;
  setupCodexEvents(mainEl);
}

function cardHtml(n) {
  const profile = loadProfile();
  const lv = profile.characters[n.id]?.level ?? 0;
  return `
    <button class="card codex-card ${lv === 0 ? 'is-unknown' : ''}" data-node-id="${n.id}"
            ${lv === 0 ? 'disabled aria-label="未遇見"' : ''}>
      <div class="stars">${lv === 0 ? '？' : '★'.repeat(lv)}</div>
      <div class="name">${lv === 0 ? '???' : n.name}</div>
      ${lv > 0 ? `<div class="meta">${n.campLabel}</div>` : ''}
    </button>
  `;
}

function emptyHint(msg) {
  return `<div class="meta" style="grid-column:1/-1;">${msg}</div>`;
}

function setupCodexEvents(mainEl) {
  mainEl.querySelectorAll('.chip').forEach(c => {
    c.addEventListener('click', () => {
      activeCampFilter = c.dataset.camp;
      renderCodex(mainEl);
    });
  });
  mainEl.querySelectorAll('.codex-card:not([disabled])').forEach(card => {
    card.addEventListener('click', () => showDetail(card.dataset.nodeId));
  });
}

function showDetail(nodeId) {
  const { data } = getState();
  const node = data.nodes.find(n => n.id === nodeId);
  if (!node) return;
  const personality = data.personality[nodeId];
  const profile = loadProfile();
  const charProfile = profile.characters[nodeId] || {};
  const overlay = document.createElement('div');
  overlay.className = 'codex-detail';
  overlay.innerHTML = `
    <div class="panel">
      <button class="btn" id="closeDetailBtn" style="float:right;">× 關閉</button>
      <h2>${node.name} ${'★'.repeat(charProfile.level || 0)}</h2>
      <p class="meta">${node.campLabel} · ${node.aliases.slice(0, 3).join('、')}</p>
      ${personality ? `
        <h3 style="margin-top:24px;">個性</h3>
        <div class="meta">標籤：${personality.traits.join(' · ') || '尚未顯露'}</div>
        ${Object.entries(personality.ratios).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([cat, ratio]) => `
          <div class="trait-bar">
            <span class="meta" style="min-width:80px;">${cat}</span>
            <span class="bar"><span class="fill" style="width:${Math.round(ratio * 100)}%"></span></span>
            <span class="meta">${Math.round(ratio * 100)}%</span>
          </div>
        `).join('')}
      ` : '<p class="meta">尚未取得個性資料。</p>'}
      <h3 style="margin-top:24px;">原文敘述</h3>
      <p class="meta">${node.description?.split('；').slice(0, 3).join('；') || ''}</p>
    </div>
  `;
  document.body.appendChild(overlay);
  overlay.querySelector('#closeDetailBtn').addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
}
