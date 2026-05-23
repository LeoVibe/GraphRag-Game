import { renderForceGraph } from '../force-graph.js';
import { DEFAULT_PERSON, state, syncHash } from '../state.js';
import {
  avatar,
  campKey,
  chapterForNodeSegment,
  chapterLabel,
  chapterRangeLabel,
  data,
  escapeAttr,
  escapeHtml,
  firstSentence,
  isCharacterId,
  splitDescription
} from '../data.js';

const RELATION_FILTERS = ['全部', '朋友', '對手', '主從', '講話', '挫折'];
const CAMP_FILTERS = [
  ['all', '全部'],
  ['wei', '魏'],
  ['shu', '蜀'],
  ['wu', '吳'],
  ['lords', '群雄']
];

export function renderPerson(root, ctx) {
  destroyExistingForceGraph(root);
  root.innerHTML = renderPersonMode();
  mountPersonForceGraph(root, state, data, {
    onPersonChange: () => {
      syncHash();
      renderPerson(root, ctx);
    }
  });
}

function renderPersonMode() {
  const person = data.byId.get(state.personId) || data.byId.get(DEFAULT_PERSON);
  if (!person) return `<section class="panel empty-state">找不到預設人物資料。</section>`;
  const visiblePeople = filteredTrunkCharacters();
  const friendRels = personFriendRels(person.id, state.relationFilter);
  return `
    <section class="panel">
      <h3 class="panel-title">人物探險</h3>
      <p class="panel-question">想看誰身邊的人？</p>
      <div class="starter-section">
        <p class="starter-hint">初次試試 - 從三大陣營主公開始</p>
        <div class="starters">
          ${['劉備', '曹操', '孫權'].map(name => starterChip(name, person.id)).join('')}
        </div>
      </div>
      <div class="search-row">
        <input data-person-search type="search" placeholder="搜尋人物..." value="${escapeAttr(state.personSearch)}">
      </div>
      <div class="camp-filter">
        ${CAMP_FILTERS.map(([value, label]) => `<button type="button" data-action="camp-filter" data-value="${value}" class="${state.campFilter === value ? 'is-active' : ''}">${label}</button>`).join('')}
      </div>
      <p class="person-list-title">主要人物 · degree 前 30</p>
      <div class="person-list">
        ${visiblePeople.map(node => personRow(node, person.id)).join('') || `<div class="empty-state">找不到符合條件的人物。</div>`}
      </div>
    </section>
    <div class="center-stack">
      <section class="panel map-panel">
        <header class="map-header">
          <div>
            <h2 class="map-title">${escapeHtml(person.name)} 的人物關係</h2>
            <div class="map-title-sub">${escapeHtml(firstSentence(person.description))}</div>
          </div>
          <div class="map-tools"><button type="button">＋</button><button type="button">−</button><button type="button">⤢</button></div>
        </header>
        <div class="map-canvas"></div>
      </section>
      <section class="panel" style="padding:0;">
        <div class="bottom-tabs">
          <button type="button" class="bottom-tab ${state.personTab === 'friends' ? 'is-active' : ''}" data-action="person-tab" data-value="friends">朋友圈</button>
          <button type="button" class="bottom-tab ${state.personTab === 'moments' ? 'is-active' : ''}" data-action="person-tab" data-value="moments">出場時刻</button>
        </div>
        <div class="bottom-panel">
          ${state.personTab === 'friends' ? renderFriendPanel(friendRels) : renderMomentPanel(person)}
        </div>
      </section>
    </div>
    <aside class="panel">
      ${renderPersonFile(person)}
    </aside>
  `;
}

function starterChip(name, selectedId) {
  const node = data.charByName.get(name);
  if (!node) return '';
  return `
    <button class="starter-chip ${node.id === selectedId ? 'is-selected' : ''}" type="button" data-action="select-person" data-id="${escapeAttr(node.id)}" data-camp="${campKey(node)}">
      <span class="avatar">${escapeHtml(avatar(node.name))}</span>
      <span class="name">${escapeHtml(node.name)}</span>
      <span class="camp">${escapeHtml(node.campLabel || '其他')}</span>
    </button>
  `;
}

function personRow(node, selectedId) {
  return `
    <button class="person-row ${node.id === selectedId ? 'is-selected' : ''}" type="button" data-action="select-person" data-id="${escapeAttr(node.id)}" data-camp="${campKey(node)}">
      <span class="dot"></span>
      <span class="name">${escapeHtml(node.name)}</span>
      <span class="meta">出場 ${node.chapterCount || 0} 章</span>
    </button>
  `;
}

function filteredTrunkCharacters() {
  const keyword = state.personSearch.trim();
  return data.trunkCharacters.filter(node => {
    if (state.campFilter !== 'all' && campKey(node) !== state.campFilter) return false;
    if (!keyword) return true;
    return node.name.includes(keyword) || (node.aliases || []).some(alias => alias.includes(keyword));
  });
}

function destroyExistingForceGraph(container) {
  const canvas = container.querySelector('.map-canvas');
  if (canvas?._forceGraph) {
    canvas._forceGraph.destroy();
    canvas._forceGraph = null;
  }
}

function mountPersonForceGraph(container, viewState, graphData, handlers = {}) {
  const canvas = container.querySelector('.map-canvas');
  if (!canvas) return;
  if (canvas._forceGraph) {
    canvas._forceGraph.destroy();
    canvas._forceGraph = null;
  }

  const person = graphData.byId.get(viewState.personId) || graphData.byId.get(DEFAULT_PERSON);
  if (!person) return;

  const rels = personFriendRels(person.id, '全部').slice(0, 7);
  const targets = rels.map(rel => graphData.byId.get(rel.target)).filter(Boolean);
  const nodes = [
    { id: person.id, name: person.name, camp: campKey(person), isFocus: true },
    ...targets.map(node => ({ id: node.id, name: node.name, camp: campKey(node) }))
  ];
  const links = targets.map(node => ({ source: person.id, target: node.id }));

  canvas._forceGraph = renderForceGraph(canvas, nodes, links, {
    onNodeClick: node => {
      if (!node.id || node.id === viewState.personId) return;
      viewState.personId = node.id;
      handlers.onPersonChange?.(node);
    }
  });
}

function renderFriendPanel(rels) {
  return `
    <div class="relation-chips">
      ${RELATION_FILTERS.map(label => `<button type="button" class="relation-chip ${state.relationFilter === label ? 'is-active' : ''}" data-action="relation-filter" data-value="${label}">${label}</button>`).join('')}
    </div>
    <div class="relation-list">
      ${rels.map(rel => relationItem(rel)).join('') || `<div class="empty-state">這個分類暫時沒有前 10 筆人物關係。</div>`}
    </div>
  `;
}

function relationItem(rel) {
  const target = data.byId.get(rel.target);
  return `
    <button class="relation-item" type="button" data-action="select-person" data-id="${escapeAttr(rel.target)}">
      <span class="avatar">${escapeHtml(avatar(target?.name || '?'))}</span>
      <span class="meta">
        <span class="who">${escapeHtml(target?.name || rel.target)} · ${escapeHtml(rel.relationType || rel.categoryLabel || '關係')}</span>
        <span class="desc">${escapeHtml(rel.description || 'GraphRAG 關係資料')}（${chapterLabel(rel)}）</span>
      </span>
    </button>
  `;
}

function renderMomentPanel(person) {
  const segments = splitDescription(person.description);
  return `
    <div class="story-list">
      ${segments.map((text, index) => `
        <div class="story-row">
          <div class="ch">${escapeHtml(chapterForNodeSegment(person, index))}</div>
          <div class="text">${escapeHtml(text)}</div>
        </div>
      `).join('') || `<div class="empty-state">這個人物暫時沒有可拆分的出場描述。</div>`}
    </div>
  `;
}

function renderPersonFile(person) {
  const rels = data.rels.filter(rel => rel.source === person.id || rel.target === person.id);
  const relatedPeople = new Set(rels.flatMap(rel => [rel.source, rel.target]).filter(id => id !== person.id && isCharacterId(id)));
  const outgoingFriends = personFriendRels(person.id, '全部');
  const profile = data.personality[person.id];
  return `
    <h3 class="panel-title">人物檔案</h3>
    <div class="file-section">
      <div class="file-header">
        <div class="avatar">${escapeHtml(avatar(person.name))}</div>
        <div class="info">
          <div class="name">${escapeHtml(person.name)}</div>
          <div class="meta">${escapeHtml((person.aliases || [])[0] || person.typeLabel || '三國人物')}</div>
        </div>
      </div>
      <div class="badge-row">
        <span class="badge">${escapeHtml(person.campLabel || '其他')}</span>
        <span class="badge">出場 ${person.chapterCount || 0} 章</span>
        <span class="badge">關係 ${person.degree || rels.length} 條</span>
      </div>
      <div class="alias-line"><strong>別名：</strong>${escapeHtml((person.aliases || []).slice(0, 8).join('、') || '資料暫無')}</div>
    </div>
    <div class="file-section">
      <h4>關係統計</h4>
      <div class="stat-row">
        <div class="stat-cell"><div class="num">${person.chapterCount || 0}</div><div class="label">出場章</div></div>
        <div class="stat-cell"><div class="num">${relatedPeople.size}</div><div class="label">關係人</div></div>
        <div class="stat-cell"><div class="num">${outgoingFriends.length}</div><div class="label">朋友圈</div></div>
      </div>
    </div>
    <div class="file-section">
      <h4>個性</h4>
      ${renderPersonalityBars(profile)}
    </div>
    <div class="quote-card">
      ${escapeHtml(firstSentence(person.description) || '真實資料暫無人物描述。')}
      <span class="source">${escapeHtml(chapterRangeLabel(person))} · ${escapeHtml(person.typeLabel || '人物')}</span>
    </div>
  `;
}

function renderPersonalityBars(profile) {
  if (!profile || !profile.ratios) return `<div class="empty-state">尚未建立個性比例。</div>`;
  const labels = { command: '會帶人', military: '會打仗', strategy: '會謀略', kinship: '重感情', story: '懂互動', other: '多面向' };
  return Object.entries(profile.ratios)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => {
      const pct = Math.round(value * 100);
      return `
        <div class="personality-bar">
          <div class="label-row"><span>${escapeHtml(labels[key] || key)}</span><span>${pct}%</span></div>
          <div class="bar"><div class="fill" style="width:${pct}%"></div></div>
        </div>
      `;
    }).join('');
}

function personFriendRels(id, filter) {
  const all = (data.outgoing.get(id) || []).filter(rel => isCharacterId(rel.target));
  // 按 target 去重：同一個人物只保留一條 rel（weight 最高那條）
  const byTarget = new Map();
  for (const rel of all) {
    const exist = byTarget.get(rel.target);
    if (!exist || (rel.weight || 0) > (exist.weight || 0)) byTarget.set(rel.target, rel);
  }
  return [...byTarget.values()].filter(rel => matchRelationChip(rel, filter)).slice(0, 10);
}

function matchRelationChip(rel, filter) {
  if (filter === '全部') return true;
  const text = `${rel.relationType || ''}${rel.description || ''}`;
  if (filter === '朋友') return rel.category === 'kinship' || /結義|兄弟|友|相助|同盟|保護/.test(text);
  if (filter === '對手') return rel.category === 'military' || /擊|斬|攻|敵|交戰|敗|殺|截/.test(text);
  if (filter === '主從') return ['command', 'office'].includes(rel.category) || /命|統領|任|拜|派|從|隨/.test(text);
  if (filter === '講話') return rel.category === 'story' || /勸|說|請|問|薦|奏|答|論|辯/.test(text);
  if (filter === '挫折') return /敗|逃|退|失|降|困|被/.test(text);
  return true;
}
