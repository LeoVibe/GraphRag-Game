import { renderForceGraph } from '../force-graph.js';
import { hintChipHtml, bindHintChip } from '../hint-chip.js';
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
  bindHintChip(root);
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
    <section class="panel" data-region="left">
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
    <div class="center-stack" data-region="center">
      <section class="panel map-panel">
        <header class="map-header">
          <div>
            <h2 class="map-title">${escapeHtml(person.name)} 的人物關係</h2>
            <div class="map-title-sub">${escapeHtml(firstSentence(person.description))}</div>
          </div>
          <div class="map-tools"><button type="button">＋</button><button type="button">−</button><button type="button">⤢</button></div>
        </header>
        ${hintChipHtml('person')}
        <div class="map-canvas"></div>
      </section>
      <section class="panel" data-region="bottom">
        <div class="bottom-tabs">
          <button type="button" class="bottom-tab ${state.personTab === 'friends' ? 'is-active' : ''}" data-action="person-tab" data-value="friends">朋友圈</button>
          <button type="button" class="bottom-tab ${state.personTab === 'moments' ? 'is-active' : ''}" data-action="person-tab" data-value="moments">出場時刻</button>
        </div>
        <div class="bottom-panel">
          ${state.personTab === 'friends' ? renderFriendPanel(friendRels) : renderMomentPanel(person)}
        </div>
      </section>
    </div>
    <aside class="panel" data-region="right">
      ${renderPersonFile(person)}
    </aside>
  `;
}

function starterChip(name, selectedId) {
  const node = data.charByName.get(name);
  if (!node) return '';
  return `
    <button class="starter-chip ${node.id === selectedId ? 'is-selected' : ''}" type="button" data-action="select-person" data-id="${escapeAttr(node.id)}" data-camp="${campKey(node)}">
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
    <p class="panel-question">他是誰？做過什麼？</p>
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
    <div class="file-teaching">
      <h4>為什麼這 7 個人？</h4>
      <p>${getTeachingNote(person.name)}</p>
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

// 教學文案：解釋這個人物的關係圈為什麼長這樣
const TEACHING_NOTES = {
  '劉備': '身邊圍著「兄弟」（關羽、張飛）+「軍師」（諸葛亮、龐統）+「保鏢」（趙雲）+「對手」（曹操、孫權）—— 這就是「仁義」領袖的人脈邏輯。',
  '曹操': '他的圈子裡有「武將」（許褚、典韋、夏侯惇）+「謀士」（荀彧、郭嘉、賈詡）+「對手」（劉備、袁紹）—— 這就是「能用人、能打仗」的領袖。',
  '孫權': '繼承哥哥孫策的江東基業，身邊都是「父兄留下的老臣」（魯肅、黃蓋、張昭）+「自己提拔的新人」（呂蒙、諸葛瑾）。',
  '諸葛亮': '出身臥龍崗的書生，被劉備三顧茅廬請出山。連到的人物大都跟「赤壁聯盟」（周瑜、魯肅、孫權）+「蜀漢治理」（劉備、龐統）有關。',
  '關羽': '劉備的義弟與第一武將。連到的人有「兄弟」（劉備、張飛）+「故主曹操」+「對手徐晃」—— 看到的就是他「義氣」這條主線。',
  '張飛': '劉備的義弟、性格直率猛將。圖譜裡跟他連結的多是戰場關係（呂布、曹操、馬超、張郃）。',
  '趙雲': '劉備帳下的「保鏢」與名將。從公孫瓚跳到劉備陣營後，長坂坡單騎救主成名。連到的人多跟「保護劉氏」有關。',
  '周瑜': '東吳少壯派統帥、赤壁之戰主角。連到的有東吳君臣（孫權、魯肅、孫策）+ 對手（曹操、諸葛亮）。',
  '呂布': '武力第一但反覆無常。連到的多是「曾經的盟友後來的對手」（董卓、王允、貂蟬、劉備）—— 看到的是「沒原則」的反面教材。',
  '袁紹': '北方最大諸侯但用人不力。連到的人有「謀士被冷落」（沮授、田豐、許攸）+「武將被擊敗」（顏良、文醜）—— 看到的是「會用人」有多重要的反證。',
};

function getTeachingNote(name) {
  return TEACHING_NOTES[name] || '從這個人的關係網，可以看到他在三國裡扮演什麼角色、跟誰結盟、跟誰對抗。點任一個人物可以切換成他的視角繼續探險。';
}

// 經典劇情 neighbors — top 10 核心人物的「該認識的人」按故事重要性排序
const LEGENDARY_NEIGHBORS = {
  '劉備': ['關羽', '張飛', '諸葛亮', '趙雲', '徐庶', '龐統', '孫權', '曹操'],
  '曹操': ['許褚', '典韋', '夏侯惇', '荀彧', '郭嘉', '張遼', '劉備', '袁紹'],
  '孫權': ['周瑜', '魯肅', '孫策', '張昭', '呂蒙', '黃蓋', '諸葛瑾', '劉備'],
  '諸葛亮': ['劉備', '周瑜', '魯肅', '龐統', '徐庶', '孫權', '張飛', '關羽'],
  '關羽': ['劉備', '張飛', '曹操', '黃忠', '趙雲', '徐晃', '魯肅', '諸葛亮'],
  '張飛': ['劉備', '關羽', '呂布', '曹操', '張郃', '馬超', '趙雲', '諸葛亮'],
  '趙雲': ['劉備', '張飛', '關羽', '諸葛亮', '公孫瓚', '張郃', '黃忠', '馬超'],
  '周瑜': ['孫權', '諸葛亮', '魯肅', '孫策', '黃蓋', '曹操', '劉備', '甘寧'],
  '呂布': ['董卓', '王允', '貂蟬', '丁原', '劉備', '曹操', '陳宮', '張飛'],
  '袁紹': ['顏良', '文醜', '許攸', '沮授', '田豐', '曹操', '公孫瓚', '袁術'],
};

function personFriendRels(id, filter) {
  const node = data.byId.get(id);
  const all = (data.outgoing.get(id) || []).filter(rel => isCharacterId(rel.target));
  // 按 target 去重：同一個人物只保留一條 rel（weight 最高那條）
  const byTarget = new Map();
  for (const rel of all) {
    const exist = byTarget.get(rel.target);
    if (!exist || (rel.weight || 0) > (exist.weight || 0)) byTarget.set(rel.target, rel);
  }
  const dedup = [...byTarget.values()];

  // 若是核心人物，按劇情排序（從 LEGENDARY_NEIGHBORS 名單）；其他按 weight
  const legendary = LEGENDARY_NEIGHBORS[node?.name];
  if (legendary) {
    const byName = new Map();
    for (const rel of dedup) {
      const tnode = data.byId.get(rel.target);
      if (tnode?.name) byName.set(tnode.name, rel);
    }
    const ordered = [];
    for (const name of legendary) {
      if (byName.has(name)) {
        ordered.push(byName.get(name));
        byName.delete(name);
      }
    }
    const rest = [...byName.values()].sort((a, b) => (b.weight || 0) - (a.weight || 0));
    return [...ordered, ...rest].filter(rel => matchRelationChip(rel, filter)).slice(0, 10);
  }

  return dedup.sort((a, b) => (b.weight || 0) - (a.weight || 0))
    .filter(rel => matchRelationChip(rel, filter)).slice(0, 10);
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
