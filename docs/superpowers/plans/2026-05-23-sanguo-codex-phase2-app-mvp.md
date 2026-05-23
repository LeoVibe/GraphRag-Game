# Sanguo Character Codex — Phase 2: 前端應用 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development。實作以 codex 為主要 implementer。每 task 完成後 controller 補 commit + review。

**Goal:** 從零實作「人物圖鑑 × 關係偵探」前端 MVP——三大區塊（主頁地圖 / 任務舞台 / 人物圖鑑）能在桌面瀏覽器跑通：孩子從地圖點關卡 → 答 3-5 題（5 種題型至少 3 種可玩）→ 看到人物卡進圖鑑、進度條 +N → 切回地圖看到進度。

**Architecture:** vanilla JS（無 framework），ES modules 拆檔。`index.html` 為薄殼，啟動載 `app.js` → `app.js` 載資料（fetch 三個 json）+ 掛載狀態管理 + 路由 → 依路由切渲染 `views/*.js` 區塊。`engine.js` 為純函式題目生成器，可獨立 unit test。`storage.js` 包裝 localStorage。狀態用 plain object + custom event 廣播變更（不引 Redux/Vuex）。

**Tech Stack:** HTML5 / CSS3 / ES2020 modules / fetch / localStorage / no build step。Node 18+ 跑 engine 單元測試（用內建 `node --test`，無外部依賴）。

**Spec 對映:**
- 主 spec `2026-05-23-sanguo-character-codex-design.md` § 3-7（整站結構、學習循環、5 題型、引擎、資料模型）
- 介面 spec `2026-05-23-sanguo-character-codex-interface-spec.md` § 3-5（桌面 layout、4 題型 UI、手機版）

**Phase 2 範圍（MVP）vs Phase 3（Polish）:**
- ✓ Phase 2：應用骨架 / 資料載入 / state / 路由 / 引擎 / 5 題型基本 UI / 三大區塊核心 UI / localStorage / 端到端跑通 / 取代 root redirect target
- ✗ Phase 3（暫不做）：三主題視覺切換 / Onboarding 3 步 / 卡關保護 / 慶祝動畫 / 完整響應式手機版 / 兒童 a11y 強化 / reduce-motion polish

Phase 2 只保證**功能跑通與資料層正確流動**，視覺刻意樸素以便加速。

**驗證標準（Phase 2 完成意味著）:**
1. 打開 `04_app/index.html` 桌面 Chrome 看得到主頁地圖、能點任一已解鎖事件包
2. 進任務舞台能看到題目主問句 + 4 選項 + 線索卡，能選一個交卷
3. 答對 / 答錯都顯示覆蓋層，答對後人物進圖鑑、進度條 +1
4. 切到圖鑑頁看到剛解鎖的人物卡片，點卡片看詳情翻面
5. Reload 頁面進度仍在
6. `node --test 04_app/engine.test.js` 至少 15 個 test pass
7. 根目錄 `三國演義探險地圖.html` 改成轉到新 `04_app/index.html`
8. v17 主檔保留在 `04_app/三國演義探險地圖_v17.html` 作 fallback

---

## File Structure

**新增（本 phase）：**
- `04_app/index.html`（薄殼）
- `04_app/app.js`（入口 + 主控）
- `04_app/storage.js`（localStorage wrapper）
- `04_app/engine.js`（題目生成純函式）
- `04_app/engine.test.js`（node --test）
- `04_app/state.js`（全域 state + event broadcast）
- `04_app/router.js`（區塊切換）
- `04_app/data.js`（fetch 三個 json + cache）
- `04_app/views/map.js`（主頁地圖渲染）
- `04_app/views/stage.js`（任務舞台渲染）
- `04_app/views/codex.js`（人物圖鑑渲染）
- `04_app/views/components.js`（共用 UI 元件：卡片、按鈕、覆蓋層）
- `04_app/styles.css`（基本樣式，Phase 2 不分主題）

**修改：**
- `三國演義探險地圖.html`（根目錄）→ redirect target 從 v17 改為 `04_app/index.html`
- `04_app/三國演義探險地圖_v17.html` → 不動，仍是 fallback

**不動：**
- 03_graphrag/*.json（資料層 read-only）
- 既有 v17 等檔（fallback 用）

---

## Task 1: 04_app 骨架（HTML 入口 + 樣式 + 純函式 module）

**Files:**
- Create: `04_app/index.html`
- Create: `04_app/styles.css`
- Create: `04_app/data.js`

### Step 1: 寫 `04_app/index.html` 薄殼

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>三國演義探險地圖 — 人物圖鑑</title>
<link rel="stylesheet" href="styles.css">
</head>
<body data-view="loading">
  <header class="top-bar">
    <h1 class="brand">三國演義探險地圖</h1>
    <div class="progress" id="topProgress" aria-label="圖鑑進度">
      <span class="progress-bar"><span class="progress-fill" id="progressFill"></span></span>
      <span class="progress-text" id="progressText">0 / 60 ★0</span>
    </div>
    <nav class="view-tabs" aria-label="主要區塊切換">
      <button data-route="map" class="tab is-active">地圖</button>
      <button data-route="stage" class="tab" disabled>任務</button>
      <button data-route="codex" class="tab">圖鑑</button>
    </nav>
  </header>
  <main id="appMain" aria-live="polite">
    <p class="loading-msg">載入資料中…</p>
  </main>
  <script type="module" src="app.js"></script>
</body>
</html>
```

### Step 2: 寫 `04_app/styles.css` 基本樣式

```css
:root {
  --color-bg: #FFF7ED;
  --color-surface: #ffffff;
  --color-text: #1E293B;
  --color-text-soft: #64748B;
  --color-primary: #F97316;
  --color-primary-strong: #C2410C;
  --color-success: #16A34A;
  --color-danger: #EF4444;
  --color-border: #E2E8F0;
  --radius-sm: 8px;
  --radius-md: 16px;
  --radius-lg: 24px;
  --shadow-card: 0 1px 3px rgba(15,23,42,.08), 0 2px 8px rgba(15,23,42,.04);
  --motion-state: 200ms ease-in-out;
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px;
  --space-5: 24px; --space-6: 32px; --space-8: 48px;
}
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh;
  font-family: "Noto Sans TC", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px; line-height: 1.6;
  color: var(--color-text); background: var(--color-bg);
}
.top-bar {
  display: flex; align-items: center; gap: var(--space-5);
  padding: var(--space-3) var(--space-5);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky; top: 0; z-index: 10;
}
.brand { margin: 0; font-size: 18px; font-weight: 700; }
.progress { display: flex; align-items: center; gap: var(--space-2); flex: 1; max-width: 360px; }
.progress-bar { flex: 1; height: 8px; background: var(--color-border); border-radius: 999px; overflow: hidden; }
.progress-fill { display: block; height: 100%; background: var(--color-primary);
  width: 0%; transition: width var(--motion-state); }
.progress-text { font-size: 14px; color: var(--color-text-soft); white-space: nowrap; }
.view-tabs { display: flex; gap: var(--space-1); }
.tab {
  padding: var(--space-2) var(--space-4); border: 1px solid var(--color-border);
  background: transparent; border-radius: var(--radius-pill, 999px);
  font: inherit; cursor: pointer; min-height: 36px;
}
.tab.is-active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.tab[disabled] { opacity: 0.4; cursor: not-allowed; }
main { padding: var(--space-5); max-width: 1200px; margin: 0 auto; }
.loading-msg { padding: var(--space-8) 0; text-align: center; color: var(--color-text-soft); }

/* Card-base */
.card {
  background: var(--color-surface); border-radius: var(--radius-md);
  padding: var(--space-4); box-shadow: var(--shadow-card); border: 1px solid var(--color-border);
}

/* Map view */
.map-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--space-4);
}
.map-node {
  text-align: left; cursor: pointer; transition: transform var(--motion-state);
  border: 2px solid var(--color-border);
}
.map-node.is-locked { opacity: 0.5; cursor: not-allowed; }
.map-node.is-active { border-color: var(--color-primary); }
.map-node:hover:not(.is-locked) { transform: translateY(-2px); }
.map-node h3 { margin: 0 0 var(--space-2); }
.map-node .meta { font-size: 14px; color: var(--color-text-soft); }
.map-node .stars { color: var(--color-primary); margin-top: var(--space-2); }

/* Stage view */
.stage { max-width: 720px; margin: 0 auto; }
.stage-question { font-size: 24px; font-weight: 600; text-align: center;
  padding: var(--space-6) var(--space-4); }
.clue-card { padding: var(--space-3); background: #FFFBEB; border-radius: var(--radius-sm);
  border: 1px solid #FDE68A; margin-bottom: var(--space-5); font-size: 14px; color: #92400E; }
.choices { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--space-3); }
.choice {
  padding: var(--space-4); border: 2px solid var(--color-border); border-radius: var(--radius-md);
  background: var(--color-surface); cursor: pointer; min-height: 88px; font: inherit;
  transition: all var(--motion-state); text-align: left;
}
.choice:hover { border-color: var(--color-primary); }
.choice.is-selected { border-color: var(--color-primary); background: #FFF7ED; }
.stage-actions { display: flex; gap: var(--space-3); justify-content: space-between;
  margin-top: var(--space-5); }
.btn { padding: var(--space-3) var(--space-5); border-radius: var(--radius-md);
  border: 1px solid var(--color-border); background: var(--color-surface); cursor: pointer;
  font: inherit; min-height: 44px; }
.btn.is-primary { background: var(--color-primary); border-color: var(--color-primary); color: #fff; }
.btn[disabled] { opacity: 0.4; cursor: not-allowed; }

/* Overlay (verdict) */
.overlay {
  position: fixed; inset: 0; background: rgba(15,23,42,0.45);
  display: flex; align-items: center; justify-content: center; padding: var(--space-4);
  z-index: 100;
}
.overlay.is-correct .panel { border-top: 4px solid var(--color-success); }
.overlay.is-wrong .panel { border-top: 4px solid var(--color-danger); }
.overlay .panel { max-width: 520px; width: 100%; background: var(--color-surface);
  border-radius: var(--radius-lg); padding: var(--space-6); }
.overlay h2 { margin-top: 0; }
.overlay .why { font-size: 15px; color: var(--color-text-soft); margin-bottom: var(--space-4); }
.overlay-actions { display: flex; gap: var(--space-3); justify-content: flex-end; }

/* Codex view */
.codex-filters { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); flex-wrap: wrap; }
.chip { padding: 6px 12px; border: 1px solid var(--color-border); border-radius: 999px;
  background: var(--color-surface); cursor: pointer; min-height: 32px; font: inherit; font-size: 14px; }
.chip.is-active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.codex-section { margin-bottom: var(--space-6); }
.codex-section h2 { font-size: 16px; color: var(--color-text-soft); margin-bottom: var(--space-3); }
.codex-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: var(--space-3);
}
.codex-card {
  padding: var(--space-3); text-align: center; cursor: pointer;
  transition: transform var(--motion-state);
}
.codex-card:hover { transform: translateY(-2px); }
.codex-card.is-unknown { opacity: 0.35; filter: grayscale(1); cursor: default; }
.codex-card .name { font-weight: 600; margin: var(--space-2) 0 0; }
.codex-card .stars { color: var(--color-primary); }

/* Detail flip */
.codex-detail {
  position: fixed; inset: 0; background: rgba(15,23,42,0.45);
  display: flex; align-items: center; justify-content: center; padding: var(--space-4); z-index: 100;
}
.codex-detail .panel { max-width: 560px; width: 100%; background: var(--color-surface);
  border-radius: var(--radius-lg); padding: var(--space-6); }
.trait-bar { display: flex; align-items: center; gap: var(--space-2); margin: var(--space-1) 0; }
.trait-bar .bar { flex: 1; height: 6px; background: var(--color-border); border-radius: 999px; overflow: hidden; }
.trait-bar .fill { display: block; height: 100%; background: var(--color-primary); }
```

### Step 3: 寫 `04_app/data.js` 資料載入

```javascript
const DATA_BASE = '../03_graphrag';
let cache = null;

export async function loadData() {
  if (cache) return cache;
  const [nodes, rels, personality] = await Promise.all([
    fetch(`${DATA_BASE}/nodes.json`).then(r => r.json()),
    fetch(`${DATA_BASE}/rels.json`).then(r => r.json()),
    fetch(`${DATA_BASE}/character_personality.json`).then(r => r.json()),
  ]);
  cache = { nodes, rels, personality };
  return cache;
}

// helpers used elsewhere
export function indexNodes(nodes) {
  const byId = new Map();
  const byName = new Map();
  for (const n of nodes) {
    byId.set(n.id, n);
    byName.set(n.name, n);
  }
  return { byId, byName };
}

export function indexRelsBySource(rels) {
  const map = new Map();
  for (const r of rels) {
    if (!map.has(r.source)) map.set(r.source, []);
    map.get(r.source).push(r);
  }
  return map;
}
```

### Step 4: 驗證 HTML 開得起來

```bash
open 04_app/index.html
```
Expected：頂部 bar 顯示「三國演義探險地圖」「0 / 60 ★0」「地圖 / 任務 / 圖鑑」，主區「載入資料中…」（因為 app.js 還沒寫）。

### Step 5: Commit（controller 補做）

---

## Task 2: state + storage + router

**Files:**
- Create: `04_app/state.js`
- Create: `04_app/storage.js`
- Create: `04_app/router.js`

### state.js

```javascript
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
```

### storage.js

```javascript
const KEY = 'sanguo-codex-v1';

const DEFAULT = {
  unlockedPacks: ['ch001_010'],  // 第一包預設解鎖
  characters: {},                // { [nodeId]: { level: 1, correctAnswers: 0, wrongAnswers: 0, discoveredEdges: [] } }
  totalStars: 0,
  recentQuestions: [],           // [questionFingerprint] 最近 20 題防重出
};

export function loadProfile() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULT };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT, ...parsed };
  } catch {
    return { ...DEFAULT };
  }
}

export function saveProfile(profile) {
  try {
    localStorage.setItem(KEY, JSON.stringify(profile));
  } catch (e) {
    console.warn('saveProfile failed', e);
  }
}

export function recordAnswer(profile, { nodeId, correct, questionFingerprint, edge }) {
  const next = { ...profile };
  next.characters = { ...next.characters };
  const cur = next.characters[nodeId] || { level: 0, correctAnswers: 0, wrongAnswers: 0, discoveredEdges: [] };
  const updated = { ...cur };
  if (correct) {
    updated.correctAnswers += 1;
    if (edge && !updated.discoveredEdges.includes(edge.id)) {
      updated.discoveredEdges = [...updated.discoveredEdges, edge.id];
    }
    // 升等規則：每 3 次正確 + ≥ 2 種題型 → +1 級（簡化：每 3 次正確 +1）
    const expectedLevel = Math.min(3, Math.floor(updated.correctAnswers / 3) + 1);
    if (expectedLevel > updated.level) {
      updated.level = expectedLevel;
      next.totalStars = next.totalStars + 1;
    }
  } else {
    updated.wrongAnswers += 1;
  }
  next.characters[nodeId] = updated;
  next.recentQuestions = [questionFingerprint, ...next.recentQuestions].slice(0, 20);
  return next;
}

export function unlockPack(profile, packId) {
  if (profile.unlockedPacks.includes(packId)) return profile;
  return { ...profile, unlockedPacks: [...profile.unlockedPacks, packId] };
}
```

### router.js

```javascript
import { getState, setState } from './state.js';

export function setupRouter() {
  // 監聽 view-tabs button
  document.querySelectorAll('[data-route]').forEach(btn => {
    btn.addEventListener('click', () => {
      const route = btn.dataset.route;
      if (btn.disabled) return;
      goto(route);
    });
  });
}

export function goto(route) {
  setState({ route, verdictOpen: null });
  document.body.dataset.view = route;
  document.querySelectorAll('[data-route]').forEach(btn => {
    btn.classList.toggle('is-active', btn.dataset.route === route);
  });
}

export function setStageEnabled(enabled) {
  const tab = document.querySelector('[data-route="stage"]');
  if (tab) tab.disabled = !enabled;
}
```

### Step: Commit（controller 補做）

---

## Task 3: 引擎核心（engine.js + engine.test.js）

**Files:**
- Create: `04_app/engine.js`
- Create: `04_app/engine.test.js`
- Test command: `node --test 04_app/engine.test.js`

### engine.js

實作以下 export：
- `CHAPTER_PACKS` — 12 個事件包定義（依主 spec § 3）
- `pickSubject(nodes, packChapterRange, profile)` — 從 isTrunk + chapter overlap 候選中加權挑一個 character
- `pickEdge(subject, rels, packChapterRange, profile)` — 取 subject 的一條 outgoing 關係
- `pickDistractors(correctNode, allNodes, edge, count=3)` — 同 camp 不同 relationType 的干擾項
- `buildQuestion({ subject, edge, allNodes, type })` — 組裝 question 物件
- `chooseQuestionType(profile, subjectLevel)` — 依等級選 L1-L4 題型
- `questionFingerprint(question)` — 防重題用

```javascript
// 12 個事件包定義
export const CHAPTER_PACKS = [
  { id: 'ch001_010', label: '英雄起義', shortLabel: '1-10', start: 1, end: 10,
    focus: '桃園結義、黃巾之亂、董卓進京' },
  { id: 'ch011_020', label: '群雄角力', shortLabel: '11-20', start: 11, end: 20,
    focus: '曹操、呂布、袁術與劉備反覆交手' },
  { id: 'ch021_030', label: '官渡前後', shortLabel: '21-30', start: 21, end: 30,
    focus: '袁紹與曹操的勢力走向決戰' },
  { id: 'ch031_040', label: '荊州伏龍', shortLabel: '31-40', start: 31, end: 40,
    focus: '劉備尋找軍師，諸葛亮開始出場' },
  { id: 'ch041_050', label: '赤壁鏖兵', shortLabel: '41-50', start: 41, end: 50,
    focus: '孫劉合作，用火攻改變三國局勢' },
  { id: 'ch051_060', label: '荊南西川', shortLabel: '51-60', start: 51, end: 60,
    focus: '三方勢力各自延伸，準備走向三足鼎立' },
];

const QUESTION_TYPES = ['who-is-this', 'what-relation', 'who-doesnt-belong'];
// MVP 先實作三種，'relation-chain', 'personality-match' 留待 Phase 3

export function chooseQuestionType(profile, subjectLevel = 0) {
  // 簡化：依據人物熟識度選題型；MVP 跑 3 種
  if (subjectLevel === 0) return 'who-is-this';
  if (subjectLevel === 1) return 'what-relation';
  return 'who-doesnt-belong';
}

export function chapterOverlap(chapters, range) {
  if (!chapters || !chapters.length) return false;
  return chapters.some(c => c >= range.start && c <= range.end);
}

export function pickSubject(nodes, pack, profile) {
  const candidates = nodes.filter(n =>
    n.kind === 'entity' && n.type === 'character' && n.isTrunk
    && chapterOverlap(n.chapters, pack)
  );
  if (!candidates.length) return null;
  // 加權挑選：已 ★★★ 熟識 → 權重 0.2；未認識 → 權重 1.0
  const weighted = candidates.map(n => {
    const level = profile.characters[n.id]?.level ?? 0;
    const weight = level >= 3 ? 0.2 : (level === 0 ? 1.0 : 0.6);
    return { node: n, weight };
  });
  return weightedPick(weighted);
}

function weightedPick(items) {
  const total = items.reduce((s, x) => s + x.weight, 0);
  let r = Math.random() * total;
  for (const it of items) {
    r -= it.weight;
    if (r <= 0) return it.node;
  }
  return items[items.length - 1].node;
}

export function pickEdge(subject, rels, pack, profile) {
  const candidates = rels.filter(r =>
    r.source === subject.id
    && chapterOverlap(r.chapters, pack)
    && r.target.startsWith('entity:character_')   // target 也必須是人物
  );
  if (!candidates.length) return null;
  // 防重出：濾掉 profile.characters[subject.id].discoveredEdges 已含的
  const discovered = new Set(profile.characters[subject.id]?.discoveredEdges || []);
  const fresh = candidates.filter(r => !discovered.has(r.id));
  const pool = fresh.length ? fresh : candidates;
  return pool[Math.floor(Math.random() * pool.length)];
}

export function pickDistractors(correctNode, allNodes, edge, count = 3) {
  // 同 camp 但不同 relationType 對應的人物
  const sameCampOthers = allNodes.filter(n =>
    n.type === 'character'
    && n.camp === correctNode.camp
    && n.id !== correctNode.id
  );
  // 排除真實 edge 對應的 target（已是答案）
  const pool = sameCampOthers.filter(n => n.id !== edge.target);
  // 按 degree 由高到低取 count 個（孩子最容易混淆的）
  pool.sort((a, b) => b.degree - a.degree);
  return pool.slice(0, count);
}

export function buildQuestion({ subject, edge, allNodes, type, byId }) {
  const correctTarget = byId.get(edge.target);
  if (!correctTarget) return null;
  let question;
  switch (type) {
    case 'who-is-this': {
      // 「下面哪一位 _ ? 跟 subject 的關係是 relationType」
      const distractors = pickDistractors(correctTarget, allNodes, edge);
      const choices = shuffle([correctTarget, ...distractors]);
      question = {
        type, subject, edge,
        prompt: `跟「${subject.name}」${edge.relationType}的是哪一位？`,
        clue: edge.description?.split('；')[0] || '',
        choices,
        correctChoiceId: correctTarget.id,
      };
      break;
    }
    case 'what-relation': {
      // 「subject 跟 correctTarget 是什麼關係？」
      const correctCategory = edge.category;
      const otherCategories = ['kinship', 'command', 'military', 'strategy']
        .filter(c => c !== correctCategory)
        .slice(0, 3);
      const allCats = shuffle([correctCategory, ...otherCategories]);
      question = {
        type, subject, edge,
        prompt: `「${subject.name}」跟「${correctTarget.name}」是什麼關係？`,
        clue: edge.description?.split('；')[0] || '',
        choices: allCats.map(c => ({ id: c, name: CATEGORY_DISPLAY[c] || c })),
        correctChoiceId: correctCategory,
      };
      break;
    }
    case 'who-doesnt-belong': {
      // 給 4 人，3 個同 camp，1 個不同
      const sameCamp = allNodes.filter(n =>
        n.type === 'character' && n.camp === subject.camp && n.id !== subject.id
      ).slice(0, 3);
      const otherCamp = allNodes.find(n =>
        n.type === 'character' && n.camp !== subject.camp && n.camp !== 'other' && n.isTrunk
      );
      if (!otherCamp || sameCamp.length < 3) return null;
      const choices = shuffle([...sameCamp, otherCamp]);
      question = {
        type, subject, edge: null,
        prompt: `下面哪一位不是「${CAMP_DISPLAY[subject.camp]}」？`,
        clue: '',
        choices,
        correctChoiceId: otherCamp.id,
      };
      break;
    }
    default:
      return null;
  }
  return question;
}

const CATEGORY_DISPLAY = {
  command: '主從／統率', military: '戰鬥／對戰',
  strategy: '計策／謀略', kinship: '親族／結拜',
  place: '同處', office: '官職', object: '物件',
  story: '同一段故事', other: '其他',
};

const CAMP_DISPLAY = {
  wei: '曹魏', shu: '劉蜀', wu: '東吳',
  lords: '群雄', mixed: '混合', other: '其他',
};

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function questionFingerprint(q) {
  return `${q.type}|${q.subject.id}|${q.edge?.id || ''}|${q.correctChoiceId}`;
}
```

### engine.test.js

```javascript
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import {
  CHAPTER_PACKS, chooseQuestionType, chapterOverlap, pickSubject,
  pickEdge, pickDistractors, buildQuestion, questionFingerprint,
} from './engine.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const nodes = JSON.parse(readFileSync(`${REPO_ROOT}/03_graphrag/nodes.json`));
const rels = JSON.parse(readFileSync(`${REPO_ROOT}/03_graphrag/rels.json`));
const byId = new Map(nodes.map(n => [n.id, n]));
const EMPTY_PROFILE = { unlockedPacks: ['ch001_010'], characters: {}, totalStars: 0, recentQuestions: [] };

test('CHAPTER_PACKS 有 6 包 cover 1-60', () => {
  assert.equal(CHAPTER_PACKS.length, 6);
  assert.equal(CHAPTER_PACKS[0].start, 1);
  assert.equal(CHAPTER_PACKS[CHAPTER_PACKS.length - 1].end, 60);
});

test('chapterOverlap 正確判定', () => {
  assert.equal(chapterOverlap([5, 7, 9], { start: 1, end: 10 }), true);
  assert.equal(chapterOverlap([15, 17], { start: 1, end: 10 }), false);
  assert.equal(chapterOverlap([], { start: 1, end: 10 }), false);
});

test('pickSubject 從 ch001_010 包能挑出 isTrunk character', () => {
  const subj = pickSubject(nodes, CHAPTER_PACKS[0], EMPTY_PROFILE);
  assert.ok(subj, '應該挑得到主角');
  assert.equal(subj.type, 'character');
  assert.equal(subj.isTrunk, true);
  assert.ok(subj.chapters.some(c => c <= 10));
});

test('pickSubject 對未知章節範圍應 return null', () => {
  const subj = pickSubject(nodes, { start: 999, end: 1000 }, EMPTY_PROFILE);
  assert.equal(subj, null);
});

test('pickEdge 取主角的 outgoing character→character 關係', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  assert.ok(edge, '曹操在 1-10 章應有 outgoing rel');
  assert.equal(edge.source, cao.id);
  assert.ok(edge.target.startsWith('entity:character_'));
});

test('pickDistractors 取得 3 個同 camp 不同 id 人物', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const liu = nodes.find(n => n.name === '劉備' && n.type === 'character');
  const fakeEdge = { target: liu.id };
  const distractors = pickDistractors(liu, nodes, fakeEdge);
  assert.equal(distractors.length, 3);
  for (const d of distractors) {
    assert.equal(d.camp, liu.camp);
    assert.notEqual(d.id, liu.id);
  }
});

test('buildQuestion who-is-this 結構正確', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'who-is-this', byId });
  assert.ok(q, '應該建得起來');
  assert.equal(q.type, 'who-is-this');
  assert.equal(q.choices.length, 4);
  assert.ok(q.choices.find(c => c.id === q.correctChoiceId));
  assert.ok(q.prompt.includes(cao.name));
});

test('buildQuestion what-relation 給 4 個 category 選項', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'what-relation', byId });
  assert.ok(q);
  assert.equal(q.choices.length, 4);
  assert.ok(q.choices.find(c => c.id === q.correctChoiceId));
});

test('buildQuestion who-doesnt-belong 找一個不同 camp', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const q = buildQuestion({ subject: cao, edge: null, allNodes: nodes, type: 'who-doesnt-belong', byId });
  if (q) {
    assert.equal(q.choices.length, 4);
    const correct = q.choices.find(c => c.id === q.correctChoiceId);
    assert.notEqual(correct.camp, cao.camp);
  }
});

test('questionFingerprint 對同問題回傳相同 hash', () => {
  const q1 = { type: 'who-is-this', subject: { id: 'a' }, edge: { id: 'e1' }, correctChoiceId: 'c1' };
  const q2 = { type: 'who-is-this', subject: { id: 'a' }, edge: { id: 'e1' }, correctChoiceId: 'c1' };
  assert.equal(questionFingerprint(q1), questionFingerprint(q2));
});

test('chooseQuestionType 對未認識（level 0）給 who-is-this', () => {
  assert.equal(chooseQuestionType(EMPTY_PROFILE, 0), 'who-is-this');
});

test('連續 10 次 pickSubject + buildQuestion 都成功', () => {
  for (let i = 0; i < 10; i++) {
    const subj = pickSubject(nodes, CHAPTER_PACKS[0], EMPTY_PROFILE);
    const edge = pickEdge(subj, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
    if (edge) {
      const q = buildQuestion({ subject: subj, edge, allNodes: nodes, type: 'who-is-this', byId });
      assert.ok(q, `iteration ${i} build 失敗`);
    }
  }
});

test('包 ch031_040 能挑出諸葛亮（驗證 data fix）', () => {
  const subjs = [];
  for (let i = 0; i < 50; i++) {
    const s = pickSubject(nodes, CHAPTER_PACKS[3], EMPTY_PROFILE);
    if (s) subjs.push(s.name);
  }
  // 50 次抽取應該至少有一次抽到諸葛亮（他 isTrunk 且 chapters 含 36+）
  assert.ok(subjs.includes('諸葛亮'), `50 次抽樣應含諸葛亮，實際: ${[...new Set(subjs)]}`);
});

test('每條 choice 都有 name 屬性', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const edge = pickEdge(cao, rels, CHAPTER_PACKS[0], EMPTY_PROFILE);
  const q = buildQuestion({ subject: cao, edge, allNodes: nodes, type: 'who-is-this', byId });
  for (const c of q.choices) assert.ok(c.name);
});
```

### Step: 跑 test

```bash
node --test 04_app/engine.test.js
```
Expected：14 tests pass。

### Step: Commit（controller 補）

---

## Task 4: views/map.js — 主頁地圖渲染

**Files:**
- Create: `04_app/views/map.js`

```javascript
import { CHAPTER_PACKS } from '../engine.js';
import { goto } from '../router.js';
import { getState, setState } from '../state.js';
import { loadProfile, unlockPack, saveProfile } from '../storage.js';

export function renderMap(mainEl) {
  const profile = loadProfile();
  mainEl.innerHTML = `
    <section class="map-grid" aria-label="事件包選擇">
      ${CHAPTER_PACKS.map(pack => mapNodeHtml(pack, profile)).join('')}
    </section>
  `;
  mainEl.querySelectorAll('.map-node').forEach(el => {
    el.addEventListener('click', () => {
      const packId = el.dataset.packId;
      const pack = CHAPTER_PACKS.find(p => p.id === packId);
      if (!profile.unlockedPacks.includes(packId)) {
        el.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(-6px)' },
          { transform: 'translateX(6px)' }, { transform: 'translateX(0)' }], { duration: 250 });
        return;
      }
      setState({ currentPackId: packId, questionsAnswered: 0, currentQuestion: null });
      document.querySelector('[data-route="stage"]').disabled = false;
      goto('stage');
    });
  });
}

function mapNodeHtml(pack, profile) {
  const isUnlocked = profile.unlockedPacks.includes(pack.id);
  const completedCount = Object.entries(profile.characters)
    .filter(([, c]) => c.level >= 1).length;
  const lockIcon = isUnlocked ? '' : '🔒';
  const stars = isUnlocked ? '★★★☆☆' : '';
  return `
    <button class="card map-node ${isUnlocked ? '' : 'is-locked'}" data-pack-id="${pack.id}">
      <h3>${lockIcon} ${pack.label}</h3>
      <div class="meta">第 ${pack.start}-${pack.end} 回</div>
      <div class="meta">${pack.focus}</div>
      ${stars ? `<div class="stars">${stars}</div>` : ''}
    </button>
  `;
}
```

---

## Task 5: views/stage.js — 任務舞台渲染

**Files:**
- Create: `04_app/views/stage.js`

實作：
- 從 state 拿 currentPackId
- 用 engine.buildQuestion 產出一題
- 渲染 prompt + clue + choices
- 「交卷」按鈕觸發 verdict overlay
- verdict overlay 顯示「答對 / 答錯」+ 「下一題 / 回地圖」
- 答對：呼叫 storage.recordAnswer 更新 profile，state 廣播
- 連答達 questionsTarget 後解鎖下一包

```javascript
import { CHAPTER_PACKS, pickSubject, pickEdge, buildQuestion, chooseQuestionType, questionFingerprint } from '../engine.js';
import { getState, setState } from '../state.js';
import { loadProfile, saveProfile, recordAnswer, unlockPack } from '../storage.js';
import { goto } from '../router.js';
import { updateProgress } from './components.js';

export function renderStage(mainEl) {
  const state = getState();
  const pack = CHAPTER_PACKS.find(p => p.id === state.currentPackId);
  if (!pack) {
    mainEl.innerHTML = '<p>請先從地圖選擇關卡。</p>';
    return;
  }
  if (!state.currentQuestion) {
    const q = generateNewQuestion(state, pack);
    if (!q) {
      mainEl.innerHTML = '<p>本包出不出更多題了 — 已達 MVP 邊界。</p>';
      return;
    }
    setState({ currentQuestion: q, selectedChoice: null });
  }
  const q = getState().currentQuestion;
  mainEl.innerHTML = `
    <section class="stage" aria-label="當前任務">
      <header class="stage-header">
        <span class="meta">${pack.label} · 第 ${getState().questionsAnswered + 1} / ${getState().questionsTarget} 題</span>
      </header>
      <h2 class="stage-question">${q.prompt}</h2>
      ${q.clue ? `<div class="clue-card">線索：${q.clue}</div>` : ''}
      <div class="choices" role="radiogroup">
        ${q.choices.map(c => `
          <button class="choice" role="radio" aria-checked="false"
                  data-choice-id="${c.id}">${c.name}</button>
        `).join('')}
      </div>
      <div class="stage-actions">
        <button class="btn" id="skipBtn">換題目</button>
        <button class="btn is-primary" id="submitBtn" disabled>交卷</button>
      </div>
    </section>
  `;
  setupStageEvents(mainEl, q, pack);
}

function generateNewQuestion(state, pack) {
  const { data } = state;
  if (!data) return null;
  const { nodes, rels } = data;
  const byId = new Map(nodes.map(n => [n.id, n]));
  const profile = loadProfile();
  for (let attempt = 0; attempt < 20; attempt++) {
    const subject = pickSubject(nodes, pack, profile);
    if (!subject) continue;
    const subjectLevel = profile.characters[subject.id]?.level ?? 0;
    const type = chooseQuestionType(profile, subjectLevel);
    if (type === 'who-doesnt-belong') {
      const q = buildQuestion({ subject, edge: null, allNodes: nodes, type, byId });
      if (q) return q;
      continue;
    }
    const edge = pickEdge(subject, rels, pack, profile);
    if (!edge) continue;
    const q = buildQuestion({ subject, edge, allNodes: nodes, type, byId });
    if (!q) continue;
    if (profile.recentQuestions.includes(questionFingerprint(q))) continue;
    return q;
  }
  return null;
}

function setupStageEvents(mainEl, q, pack) {
  mainEl.querySelectorAll('.choice').forEach(btn => {
    btn.addEventListener('click', () => {
      mainEl.querySelectorAll('.choice').forEach(b => {
        b.classList.remove('is-selected');
        b.setAttribute('aria-checked', 'false');
      });
      btn.classList.add('is-selected');
      btn.setAttribute('aria-checked', 'true');
      setState({ selectedChoice: btn.dataset.choiceId });
      mainEl.querySelector('#submitBtn').disabled = false;
    });
  });
  mainEl.querySelector('#submitBtn').addEventListener('click', () => {
    submit(q, pack, mainEl);
  });
  mainEl.querySelector('#skipBtn').addEventListener('click', () => {
    setState({ currentQuestion: null, selectedChoice: null });
    renderStage(mainEl);
  });
}

function submit(q, pack, mainEl) {
  const chosen = getState().selectedChoice;
  const correct = chosen === q.correctChoiceId;
  const profile = loadProfile();
  const subject = q.subject;
  const explanation = q.edge?.description?.split('；')[0] || `${subject.name} 跟 ${q.choices.find(c => c.id === q.correctChoiceId)?.name} 在這場故事裡有關聯。`;
  const updated = recordAnswer(profile, {
    nodeId: subject.id,
    correct,
    questionFingerprint: questionFingerprint(q),
    edge: q.edge,
  });
  saveProfile(updated);
  showVerdict(mainEl, { correct, explanation, q, pack, updated });
}

function showVerdict(mainEl, { correct, explanation, q, pack, updated }) {
  const overlay = document.createElement('div');
  overlay.className = `overlay ${correct ? 'is-correct' : 'is-wrong'}`;
  overlay.innerHTML = `
    <div class="panel">
      <h2>${correct ? '✨ 答對了！' : '再想想看，差一點 🌱'}</h2>
      <p class="why">${explanation}</p>
      <div class="overlay-actions">
        <button class="btn" id="nextBtn">下一題</button>
        <button class="btn is-primary" id="backBtn">回地圖</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);
  updateProgress(updated);
  overlay.querySelector('#nextBtn').addEventListener('click', () => {
    overlay.remove();
    const nextAnswered = getState().questionsAnswered + 1;
    setState({ currentQuestion: null, selectedChoice: null, questionsAnswered: nextAnswered });
    if (nextAnswered >= getState().questionsTarget) {
      const nextPack = unlockNextPack(updated, pack);
      saveProfile(nextPack);
      alert('本關卡完成！下一包已解鎖。');
      goto('map');
    } else {
      renderStage(mainEl);
    }
  });
  overlay.querySelector('#backBtn').addEventListener('click', () => {
    overlay.remove();
    goto('map');
  });
}

function unlockNextPack(profile, pack) {
  const idx = CHAPTER_PACKS.findIndex(p => p.id === pack.id);
  if (idx === -1 || idx === CHAPTER_PACKS.length - 1) return profile;
  const next = CHAPTER_PACKS[idx + 1];
  return unlockPack(profile, next.id);
}
```

---

## Task 6: views/codex.js — 人物圖鑑

**Files:**
- Create: `04_app/views/codex.js`

```javascript
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
```

---

## Task 7: views/components.js + app.js（整合）

**Files:**
- Create: `04_app/views/components.js`（含 updateProgress 等共用元件）
- Create: `04_app/app.js`（入口）

### views/components.js

```javascript
import { loadProfile } from '../storage.js';

export function updateProgress(profile = null) {
  const p = profile || loadProfile();
  const known = Object.values(p.characters).filter(c => c.level >= 1).length;
  const fill = document.getElementById('progressFill');
  const text = document.getElementById('progressText');
  const target = 60;
  if (fill) fill.style.width = `${Math.min(100, (known / target) * 100)}%`;
  if (text) text.textContent = `${known} / ${target} ★${p.totalStars}`;
}
```

### app.js

```javascript
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
    setupRouter();
    updateProgress();
    subscribe(state => renderRoute(state));
    renderRoute(getState());
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
```

### Step: 開啟瀏覽器測試

```bash
open 04_app/index.html
```

Expected end-to-end：
1. 頁面載入完顯示「主頁地圖」6 個事件包卡片，第一包 `英雄起義` 已解鎖（無 🔒），其他 5 個有鎖
2. 點 `英雄起義` 卡片 → 自動切到「任務」tab → 顯示題目 + 4 個選項 + 線索卡
3. 選一個答案 → 「交卷」變亮 → 點 → 覆蓋層出現「答對 ✨」或「再想想看 🌱」+ 解釋
4. 「下一題」→ 繼續同包；連答 5 題 → 跳 `alert("本關卡完成！下一包已解鎖。")` → 回地圖看到第 2 包解鎖
5. 切到「圖鑑」tab → 看到剛答對解鎖的人物卡（★ 1 或 2）
6. 點任一已解鎖卡片 → 看到詳情：個性 traits + ratios bar + 原文敘述
7. 整頁 Reload → 進度條仍顯示之前的解鎖數

### Step: Commit（controller 補）

---

## Task 8: 切換根目錄 redirect target 到新 index.html

**Files:**
- Modify: `三國演義探險地圖.html`（根目錄）

把 redirect target 從 `04_app/三國演義探險地圖_v17.html` 改為 `04_app/index.html`。

```html
<meta http-equiv="refresh" content="0; url=04_app/index.html">
<link rel="canonical" href="04_app/index.html">
...
<a href="04_app/index.html">點此手動進入</a>
...
location.replace('04_app/index.html');
```

並更新 caption：「正在帶你前往最新版本…」維持。

### Step: Commit（controller 補）

---

## Phase 2 完成檢查清單

- [ ] `04_app/index.html` `app.js` `engine.js` `engine.test.js` `state.js` `storage.js` `router.js` `data.js` 全部存在
- [ ] `04_app/views/map.js` `stage.js` `codex.js` `components.js` 全部存在
- [ ] `04_app/styles.css` 存在
- [ ] `node --test 04_app/engine.test.js` ≥ 14 tests pass
- [ ] 瀏覽器打開 `04_app/index.html` 三大區塊都能切換
- [ ] 答對一題後，進度條 +1、圖鑑出現該人物卡
- [ ] Reload 後進度仍在
- [ ] 根目錄 `三國演義探險地圖.html` 跳到 `04_app/index.html`（不再跳 v17）
- [ ] 第一包答完 5 題後自動解鎖第二包
- [ ] git history 乾淨

## Phase 3 預告（不在本 plan）

- 三主題 CSS（classic / bamboo / warroom）切換到三大區塊
- Onboarding 3 步輕觸引導
- 卡關保護機制（連錯 3 題啟動提示模式、5 題自動通關）
- 進度感慶祝動畫（升等動畫、解鎖 toast、彩帶）
- 完整響應式手機 layout（拇指區 / 安全距離 / 2×2 候選網格）
- 兒童 a11y 強化（對比 ≥ 7:1、reduce-motion fallback、字級切換）
- 個性配對題（拖拉互動）+ 關係鏈題（多跳推理）
- 在地圖上看連接圖譜（從覆蓋層點下去）
