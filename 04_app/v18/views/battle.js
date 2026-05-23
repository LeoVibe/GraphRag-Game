import { STEP_CATEGORIES, STEP_META, STEP_ORDER, BATTLES } from '../battle-presets.js';
import { renderForceGraph } from '../force-graph.js';
import { currentBattle, state } from '../state.js';
import {
  avatar,
  campKey,
  chapterLabel,
  data,
  escapeHtml,
  mergeRels,
  nodeName,
  range,
  resolveAnyId,
  resolveAnyNode
} from '../data.js';

export function renderBattle(root, ctx) {
  destroyExistingForceGraph(root);
  root.innerHTML = renderBattleMode();
  mountBattleForceGraph(root.querySelector('.map-canvas'), currentBattle(), ctx);
}

function renderBattleMode() {
  const battle = currentBattle();
  const visibleBattles = BATTLES.filter(item => !state.battleSearch.trim() || item.name.includes(state.battleSearch.trim()));
  return `
    <section class="panel" data-region="left">
      <h3 class="panel-title">戰役推理</h3>
      <p class="panel-question">想知道哪場戰役怎麼打？</p>
      <input class="battle-search" data-battle-search type="search" placeholder="搜尋戰役..." value="${escapeHtml(state.battleSearch)}">
      <div class="battle-list">
        ${visibleBattles.map(item => battleCard(item, battle.key)).join('') || `<div class="empty-state">找不到符合的戰役。</div>`}
      </div>
    </section>
    <div class="center-stack" data-region="center">
      <section class="panel map-panel">
        <header class="map-header">
          <div>
            <h2 class="map-title">${escapeHtml(battle.name)}</h2>
            <div class="map-title-sub">${escapeHtml(battle.coreQuestion)}</div>
          </div>
          <div class="map-tools"><button type="button">＋</button><button type="button">−</button><button type="button">⤢</button></div>
        </header>
        <div class="map-canvas"></div>
      </section>
      <section class="panel" data-region="bottom">
        <div class="bottom-tabs">
          ${STEP_ORDER.map(key => stepTab(key)).join('')}
        </div>
        <div class="bottom-panel">
          ${renderReasoningContent(battle)}
        </div>
      </section>
    </div>
    <aside class="panel" data-region="right">
      ${renderBattleFile(battle)}
    </aside>
  `;
}

function battleCard(battle, selectedKey) {
  return `
    <button class="battle-card ${battle.key === selectedKey ? 'is-selected' : ''}" type="button" data-action="select-battle" data-key="${battle.key}">
      <div class="bc-chapters">第 ${battle.chapters[0]}-${battle.chapters[1]} 回</div>
      <div class="bc-name">${escapeHtml(battle.name)}</div>
      <div class="bc-period">${escapeHtml(battle.period)}</div>
      <div class="bc-vs">
        <span class="vs-side ${battle.sideA.camp}">${escapeHtml(battle.sideA.leader)}</span>
        <span class="vs-sep">對</span>
        <span class="vs-side ${battle.sideB.camp}">${escapeHtml(battle.sideB.leader)}</span>
      </div>
    </button>
  `;
}

function stepTab(key) {
  const meta = STEP_META[key];
  return `
    <button class="bottom-tab ${state.reasoningStep === key ? 'is-active' : ''}" type="button" data-action="reasoning-step" data-value="${key}">
      <span class="step-num">${meta.num}</span>
      <span class="step-label">${meta.label}</span>
      <span class="step-sub">${meta.sub}</span>
    </button>
  `;
}

function renderReasoningContent(battle) {
  const meta = STEP_META[state.reasoningStep];
  const cards = evidenceForBattle(battle, state.reasoningStep);
  return `
    <h4 class="step-q">${escapeHtml(meta.q)}</h4>
    <div class="evidence-grid">
      ${cards.map(evidenceCard).join('') || `<div class="empty-state">真實關係資料中暫時找不到這一步的明確證據卡。</div>`}
    </div>
  `;
}

function evidenceCard(rel) {
  const who = evidenceWho(rel);
  return `
    <div class="evidence-card">
      <div class="who-avatar" data-camp="${campKey(who)}">${escapeHtml(avatar(who?.name || '?'))}</div>
      <div class="ev-text">
        <span class="who">${escapeHtml(who?.name || '關係資料')}</span>
        <span class="what">${escapeHtml(rel.description || rel.relationType || 'GraphRAG 證據')}</span>
        <span class="ch">${escapeHtml(chapterLabel(rel))} · ${escapeHtml(rel.categoryLabel || rel.category)}</span>
      </div>
    </div>
  `;
}

function evidenceForBattle(battle, step) {
  const participantIds = new Set(battleParticipantIds(battle));
  const leaderIds = new Set([resolveAnyId(battle.sideA.lookup || battle.sideA.leader), resolveAnyId(battle.sideB.lookup || battle.sideB.leader)].filter(Boolean));
  const categories = STEP_CATEGORIES[step];
  const resultMode = step === 'result';
  let candidates = data.rels.filter(rel => {
    if (resultMode) {
      if (!(rel.category === 'defeat' || (rel.category === 'military' && /敗/.test(`${rel.relationType || ''}${rel.description || ''}`)))) return false;
    } else if (!categories.includes(rel.category)) {
      return false;
    }
    if (step === 'cause' && !endpointMatches(rel, leaderIds) && !textMatchesNames(rel, [battle.sideA.leader, battle.sideB.leader])) return false;
    return relMatchesBattle(rel, battle, participantIds);
  });
  if (candidates.length < 4) {
    const relaxed = data.rels.filter(rel => {
      if (resultMode) {
        if (!(rel.category === 'defeat' || (rel.category === 'military' && /敗/.test(`${rel.relationType || ''}${rel.description || ''}`)))) return false;
        return overlapsChapters(rel, battle.chapters) || endpointMatches(rel, participantIds) || textMatchesNames(rel, battleNames(battle));
      } else if (!categories.includes(rel.category)) {
        return false;
      }
      return overlapsChapters(rel, battle.chapters) && (endpointMatches(rel, participantIds) || textMatchesNames(rel, battleNames(battle)));
    });
    candidates = mergeRels(candidates, relaxed);
  }
  return candidates
    .sort((a, b) => evidenceScore(b, participantIds, battle) - evidenceScore(a, participantIds, battle))
    .slice(0, 6);
}

function destroyExistingForceGraph(container) {
  const canvas = container.querySelector('.map-canvas');
  if (canvas?._forceGraph) {
    canvas._forceGraph.destroy();
    canvas._forceGraph = null;
  }
}

function mountBattleForceGraph(canvas, battle, handlers = {}) {
  if (!canvas) return;
  if (canvas._forceGraph) {
    canvas._forceGraph.destroy();
    canvas._forceGraph = null;
  }

  const centerId = 'battle-center';
  const left = [battle.sideA.leader, ...battle.sideA.members].slice(0, 5);
  const right = [battle.sideB.leader, ...battle.sideB.members].slice(0, 5);
  const commanders = [
    ...left.map((name, index) => commanderForceNode(name, battle.sideA, 'left', index)),
    ...right.map((name, index) => commanderForceNode(name, battle.sideB, 'right', index))
  ];
  const nodes = [
    { id: centerId, name: battle.name || battle.id || battle.key, isBattleCenter: true },
    ...commanders
  ];
  const links = commanders.map(node => ({ source: centerId, target: node.id }));

  canvas._forceGraph = renderForceGraph(canvas, nodes, links, { linkDistance: 100 });
  canvas.insertAdjacentHTML('beforeend', battleSideLabels(battle));
}

function commanderForceNode(name, side, sideKey, index) {
  const node = resolveAnyNode(name);
  const campSource = node || { camp: side.camp };
  return {
    id: `${sideKey}:${node?.id || name}:${index}`,
    name: node?.name || name,
    camp: campKey(campSource)
  };
}

function battleSideLabels(battle) {
  return `
    <span class="map-side-label left">${escapeHtml(battle.sideA.label)}</span>
    <span class="map-side-label right">${escapeHtml(battle.sideB.label)}</span>
  `;
}

function renderBattleFile(battle) {
  const battleNodes = battle.nodeNames.map(name => resolveAnyNode(name)).filter(Boolean);
  const chapterPills = [...new Set(battleNodes.flatMap(node => node.chapters || []))].filter(Boolean).slice(0, 8);
  const chapters = chapterPills.length ? chapterPills : range(battle.chapters[0], battle.chapters[1]);
  return `
    <h3 class="panel-title">戰役檔案</h3>
    <p class="panel-question">雙方對陣與勝負轉折</p>
    <div class="file-section">
      <h4>雙方對陣</h4>
      <div class="vs-block">
        ${vsSide(battle.sideA)}
        <div class="vs-sep-big">對</div>
        ${vsSide(battle.sideB)}
      </div>
    </div>
    <div class="file-section">
      <h4>勝負與轉折</h4>
      <span class="outcome-badge">${escapeHtml(battle.outcome)}</span>
      <p class="outcome-text">${escapeHtml(bestBattleDescription(battle) || battle.coreQuestion)}</p>
    </div>
    <div class="file-section">
      <h4>關鍵章回</h4>
      <div class="ch-pills">${chapters.map(ch => `<span class="ch-pill">第 ${ch} 回</span>`).join('')}</div>
    </div>
    <div class="file-section">
      <h4>故事意涵</h4>
      <p class="outcome-text">${escapeHtml(battle.meaning)}</p>
    </div>
  `;
}

function vsSide(side) {
  return `
    <div class="vs-side-block">
      <div class="side-label ${side.camp}">${escapeHtml(side.label)}</div>
      <div class="commanders">
        <strong>${escapeHtml(side.leader)}</strong>
        <div style="font-size:11px; color:var(--color-text-muted);">${escapeHtml(side.members.join(' · '))}</div>
      </div>
    </div>
  `;
}

function battleParticipantIds(battle) {
  return battleNames(battle).map(name => resolveAnyId(name)).filter(Boolean);
}

function battleNames(battle) {
  return [
    battle.sideA.lookup || battle.sideA.leader,
    battle.sideA.leader,
    ...battle.sideA.members,
    battle.sideB.lookup || battle.sideB.leader,
    battle.sideB.leader,
    ...battle.sideB.members,
    ...battle.nodeNames
  ];
}

function relMatchesBattle(rel, battle, participantIds) {
  if (endpointMatches(rel, participantIds)) return overlapsChapters(rel, battle.chapters);
  if (textMatchesNames(rel, battleNames(battle))) return overlapsChapters(rel, battle.chapters);
  const battleNodeIds = new Set(battle.nodeNames.map(name => resolveAnyId(name)).filter(Boolean));
  return endpointMatches(rel, battleNodeIds);
}

function endpointMatches(rel, ids) {
  return ids.has(rel.source) || ids.has(rel.target);
}

function textMatchesNames(rel, names) {
  const text = `${rel.relationType || ''}${rel.description || ''}${nodeName(rel.source)}${nodeName(rel.target)}`;
  return names.some(name => name && text.includes(name));
}

function overlapsChapters(rel, [start, end]) {
  const relStart = rel.chapterStart || Math.min(...(rel.chapters || [start]));
  const relEnd = rel.chapterEnd || Math.max(...(rel.chapters || [end]));
  return relStart <= end && relEnd >= start;
}

function evidenceScore(rel, participantIds, battle) {
  let score = 0;
  if (endpointMatches(rel, participantIds)) score += 10;
  if (textMatchesNames(rel, [battle.sideA.leader, battle.sideB.leader, battle.name])) score += 4;
  if (overlapsChapters(rel, battle.chapters)) score += 3;
  score += rel.weight || 0;
  return score;
}

function evidenceWho(rel) {
  const source = data.byId.get(rel.source);
  const target = data.byId.get(rel.target);
  return source?.type === 'character' ? source : target?.type === 'character' ? target : source || target;
}

function bestBattleDescription(battle) {
  const nodes = battle.nodeNames.map(name => resolveAnyNode(name)).filter(Boolean);
  return nodes.map(node => node.description).find(Boolean);
}
