import { state } from '../state.js';
import {
  avatar,
  campKey,
  chapterLabel,
  data,
  escapeAttr,
  escapeHtml,
  sharedChapters
} from '../data.js';
import { segmentTag, shortestPath } from '../pathfinder.js';

const COMMON_PAIRS = [
  ['劉備', '曹操', '煮酒論英雄'],
  ['諸葛亮', '孫權', '舌戰群儒'],
  ['呂布', '劉備', '三國亂世'],
  ['關羽', '曹操', '過五關斬六將'],
  ['周瑜', '諸葛亮', '既生瑜何生亮']
];

export function renderRelation(root, ctx) {
  root.innerHTML = renderRelationMode();
}

function renderRelationMode() {
  const from = data.byId.get(state.fromId);
  const to = data.byId.get(state.toId);
  const path = from && to ? shortestPath(state.fromId, state.toId, 3) : null;
  return `
    <section class="panel">
      <h3 class="panel-title">關係路徑</h3>
      <p class="panel-question">想知道哪兩人怎麼認識？</p>
      ${endpointBlock('① 起點', from, 'clear-from')}
      <div class="swap-row"><button class="swap-btn" type="button" title="交換起點與終點" data-action="swap">⇅</button></div>
      ${endpointBlock('② 終點', to, 'clear-to')}
      <button class="find-btn" type="button">找出路徑 →</button>
      ${presetPairs()}
    </section>
    <div class="center-stack">
      ${renderPathFlow(from, to, path)}
      ${renderSegments(path)}
    </div>
    <aside class="panel">
      ${renderPathSummary(from, to, path)}
    </aside>
  `;
}

function endpointBlock(label, node, clearAction) {
  const filled = Boolean(node);
  return `
    <div class="endpoint-block ${filled ? 'is-filled' : 'is-empty'}">
      <span class="ep-label">${label}</span>
      <div class="ep-content">
        <div class="ep-avatar">${filled ? escapeHtml(avatar(node.name)) : '?'}</div>
        <div class="ep-info">
          <div class="ep-name">${filled ? escapeHtml(node.name) : '尚未選擇人物'}</div>
          <div class="ep-camp">${filled ? `${escapeHtml(node.campLabel || '其他')} · 出場 ${node.chapterCount || 0} 章` : '可用下方常用配對重新帶入'}</div>
        </div>
        ${filled ? `<button class="ep-clear" type="button" data-action="${clearAction}" aria-label="清除">×</button>` : ''}
      </div>
    </div>
  `;
}

function presetPairs() {
  return `
    <div class="preset-section">
      <h4 class="preset-title">常用配對 · 點一下立即試</h4>
      <div class="preset-list">
        ${COMMON_PAIRS.map(([from, to, hint]) => {
          const fromNode = data.charByName.get(from);
          const toNode = data.charByName.get(to);
          return `
            <button class="preset-row" type="button" data-action="preset-pair" data-from="${escapeAttr(from)}" data-to="${escapeAttr(to)}">
              <span class="pr-name ${campKey(fromNode)}">${escapeHtml(from)}</span>
              <span class="pr-arrow">→</span>
              <span class="pr-name ${campKey(toNode)}">${escapeHtml(to)}</span>
              <span class="pr-hint">${escapeHtml(hint)}</span>
            </button>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

function renderPathFlow(from, to, path) {
  if (!from || !to) {
    return `
      <section class="path-flow-panel">
        <div class="empty-state">請先選好起點與終點。找不到時可直接使用左側 5 組常用配對。</div>
      </section>
    `;
  }
  if (!path) {
    return `
      <section class="path-flow-panel">
        <div class="path-flow-title">
          <span class="from-name">${escapeHtml(from.name)}</span><span class="arrow">→</span><span class="to-name">${escapeHtml(to.name)}</span>
          <span class="label">找不到 3 跳內路徑</span>
        </div>
        <div class="empty-state">真實 character→character 關係中，3 跳內沒有找到可連接路徑。可以改用左側常用配對。</div>
      </section>
    `;
  }
  const nodeHtml = [];
  path.nodes.forEach((id, index) => {
    const node = data.byId.get(id);
    const endpoint = index === 0 || index === path.nodes.length - 1;
    nodeHtml.push(`
      <div class="path-node ${endpoint ? 'is-endpoint' : ''}">
        <span class="num">${index === 0 ? '起' : index === path.nodes.length - 1 ? '終' : index}</span>
        <div class="avatar">${escapeHtml(avatar(node?.name || '?'))}</div>
        <div class="name">${escapeHtml(node?.name || id)}</div>
        <span class="camp ${campKey(node)}">${escapeHtml(node?.campLabel || '其他')}</span>
      </div>
    `);
    if (path.edges[index]) {
      const rel = path.edges[index];
      const tag = segmentTag(rel);
      nodeHtml.push(`
        <div class="path-edge">
          <span class="edge-label">${escapeHtml(rel.relationType || rel.categoryLabel || '關係')}</span>
          <span class="edge-meta">${escapeHtml(chapterLabel(rel))} · ${tag.label}</span>
        </div>
      `);
    }
  });
  return `
    <section class="path-flow-panel">
      <div class="path-flow-title">
        <span class="from-name">${escapeHtml(from.name)}</span><span class="arrow">→</span><span class="to-name">${escapeHtml(to.name)}</span>
        <span class="label">經過 ${Math.max(0, path.nodes.length - 2)} 人 · ${path.edges.length} 段路</span>
      </div>
      <div class="path-flow">${nodeHtml.join('')}</div>
    </section>
  `;
}

function renderSegments(path) {
  if (!path) {
    return `
      <section class="panel segments-panel">
        <div class="segments-header"><h3>路徑分段閱讀</h3>${legend()}</div>
        <div class="empty-state">目前沒有可閱讀的分段。</div>
      </section>
    `;
  }
  return `
    <section class="panel segments-panel">
      <div class="segments-header"><h3>路徑分段閱讀</h3>${legend()}</div>
      <div class="segment-list">
        ${path.edges.map((rel, index) => segmentCard(rel, path.nodes[index], path.nodes[index + 1], index)).join('') || `<div class="empty-state">起點與終點相同，沒有中間分段。</div>`}
      </div>
    </section>
  `;
}

function legend() {
  return `
    <div class="legend">
      <div class="legend-item"><span class="swatch military"></span>軍事</div>
      <div class="legend-item"><span class="swatch interact"></span>互動</div>
      <div class="legend-item"><span class="swatch identity"></span>身分</div>
    </div>
  `;
}

function segmentCard(rel, fromId, toId, index) {
  const from = data.byId.get(fromId);
  const to = data.byId.get(toId);
  const tag = segmentTag(rel);
  return `
    <div class="segment">
      <div class="seg-num">${index + 1}</div>
      <div class="seg-body">
        <div class="seg-pair">
          <span class="name ${campKey(from)}">${escapeHtml(from?.name || fromId)}</span>
          <span class="arrow">→</span>
          <span class="name ${campKey(to)}">${escapeHtml(to?.name || toId)}</span>
        </div>
        <div class="seg-desc">${escapeHtml(rel.description || rel.relationType || 'GraphRAG 找到兩者相鄰。')}</div>
        <div class="seg-meta">${escapeHtml(chapterLabel(rel))} · ${escapeHtml(rel.categoryLabel || rel.category)}</div>
      </div>
      <span class="seg-tag ${tag.className}">${tag.label}</span>
    </div>
  `;
}

function renderPathSummary(from, to, path) {
  const ratio = path ? path.edges.reduce((acc, rel) => {
    acc[segmentTag(rel).className] += 1;
    return acc;
  }, { military: 0, interact: 0, identity: 0 }) : { military: 0, interact: 0, identity: 0 };
  const total = path ? Math.max(1, path.edges.length) : 1;
  return `
    <h3 class="panel-title">路徑摘要</h3>
    <p style="margin:0 0 16px; font-size:13px; color:var(--color-text-soft);">兩個人怎麼串起來？</p>
    <div class="summary-section">
      <div class="endpoints-summary">
        ${summaryEndpoint(from)}
        <div class="es-arrow">→</div>
        ${summaryEndpoint(to)}
      </div>
    </div>
    <div class="summary-section">
      <div class="stat-row">
        <div class="stat-cell"><div class="num">${path ? path.edges.length : 0}</div><div class="label">段路</div></div>
        <div class="stat-cell"><div class="num">${path ? Math.max(0, path.nodes.length - 2) : 0}</div><div class="label">中間人</div></div>
        <div class="stat-cell"><div class="num">${path ? sharedChapters(path) : 0}</div><div class="label">共同章回</div></div>
      </div>
    </div>
    <div class="summary-section">
      <h4>中間人物</h4>
      <div class="middle-list">
        ${path && path.nodes.length > 2 ? path.nodes.slice(1, -1).map((id, index) => middleItem(id, index)).join('') : `<div class="empty-state">沒有中間人物。</div>`}
      </div>
    </div>
    <div class="summary-section">
      <h4>三種證據比例</h4>
      <div class="evidence-ratio">
        ${ratioRow('軍事', 'military', ratio.military, total)}
        ${ratioRow('互動', 'interact', ratio.interact, total)}
        ${ratioRow('身分', 'identity', ratio.identity, total)}
      </div>
    </div>
    <div class="summary-section">
      <h4>故事意涵</h4>
      <p class="outcome-text">${path ? '這條路徑完全由真實 character→character 關係組成，可逐段回讀關係描述與章回。' : '目前沒有 3 跳內路徑，請換一組人物或使用常用配對。'}</p>
    </div>
  `;
}

function summaryEndpoint(node) {
  return `
    <div class="es-side">
      <div class="ava">${node ? escapeHtml(avatar(node.name)) : '?'}</div>
      <div class="nm">${node ? escapeHtml(node.name) : '未選擇'}</div>
      <div class="cp">${node ? escapeHtml(node.campLabel || '其他') : '-'}</div>
    </div>
  `;
}

function middleItem(id, index) {
  const node = data.byId.get(id);
  return `
    <div class="middle-item">
      <span class="mi-num">${index + 1}</span>
      <span class="mi-name">${escapeHtml(node?.name || id)}</span>
      <span class="mi-camp">${escapeHtml(node?.campLabel || '其他')}</span>
    </div>
  `;
}

function ratioRow(label, className, value, total) {
  const pct = Math.round((value / total) * 100);
  return `
    <div class="evi-row">
      <span class="lbl">${label}</span>
      <div class="bar"><div class="fill ${className}" style="width:${pct}%;"></div></div>
      <span class="pct">${value} 段</span>
    </div>
  `;
}
