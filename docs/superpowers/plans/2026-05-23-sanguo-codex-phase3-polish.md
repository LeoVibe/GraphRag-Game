# Sanguo Character Codex — Phase 3: Polish & Friendly UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development。每 task 完成後 controller 補 commit + browser e2e check。

**Goal:** 把 Phase 2 MVP（功能跑通）升級為「孩子打開就想玩、玩了不想關」的成品。涵蓋三主題視覺、剩 2 個題型、Onboarding、卡關保護、慶祝動畫、響應式手機 layout、兒童 a11y 強化。

**Architecture:** 不動 Phase 2 已有的資料層、引擎核心、view 主結構；新增 `themes.css`（三主題色票）、`views/onboarding.js`（3 步引導）、`safeguards.js`（卡關保護邏輯）、`views/celebrations.js`（toast / 升等動畫）、`engine.js` 補 `'relation-chain'` 與 `'personality-match'` 兩種題型 builder。整體仍保持 vanilla JS、無 build step。

**Tech Stack:** 沿用 Phase 2（HTML5 / CSS3 / ES2020 modules / fetch / localStorage / no build）。新增 CSS prefers-reduced-motion 與 prefers-contrast media query 處理。

**Spec 對映：** Interface spec § 1（三主題對映）、§ 2（Design Tokens）、§ 4（4 題型 UI 含 personality-match / relation-chain）、§ 5（手機 layout）、§ 6（兒童 a11y 11 條）、§ 7（友善設計 / 卡關保護 / 進度感）。

**驗證標準（Phase 3 完成意味著）:**
1. 三大區塊切換時可見 body class 從 `style-bamboo` → `style-warroom` → `style-classic`，背景 / 卡片質感 / 配色明顯不同
2. 首次進站顯示 3 步 onboarding，可跳過、再次進站不再出現
3. 連錯 3 題自動顯示提示（線索區多一條），連錯 5 題顯示「沒關係，先過去」並自動 next
4. 答對 5 題（升 1 ★）有彈跳動畫 + 「新人物入袋」toast 3 秒
5. 手機 375px viewport 任務舞台候選改 2×2 grid，主 CTA 在底部右側拇指區
6. 字級切換「小 / 中 / 大」生效全站
7. 開 OS reduce-motion 後所有 spring → 80ms fade
8. 主文字對比 ≥ 7:1（AAA）— 用 chrome devtools snapshot 驗證
9. 個性配對 / 關係鏈兩題型 UI 跑通、`node --test` 至少 +6 tests pass
10. v17 / 舊版 HTML 仍能 fallback（不破壞既有）

---

## File Structure

**新增（本 phase）：**
- `04_app/themes.css` — 三主題色票 + body.style-* class
- `04_app/safeguards.js` — 卡關保護邏輯（連錯計數、提示模式、強制通關）
- `04_app/views/onboarding.js` — 首次進站 3 步引導
- `04_app/views/celebrations.js` — toast、升等動畫、彩帶
- `04_app/views/dnd.js` — 拖拉互動（給個性配對題用）
- 額外 unit tests in `04_app/engine.test.js`（+ 6 tests for 2 新題型）

**修改（少量）：**
- `04_app/index.html` — 加 themes.css link、字級切換按鈕
- `04_app/styles.css` — 抽出非主題的 layout 與 motion；補手機 media query
- `04_app/app.js` — onboarding gate、subscribe 設 body class 主題
- `04_app/router.js` — `goto(route)` 時切換 body.dataset.theme
- `04_app/views/stage.js` — 整合 safeguards（連錯處理）、慶祝動畫、補關係鏈與個性配對 UI 分支
- `04_app/views/codex.js` — 卡片詳情升級（traits 動畫 bar）
- `04_app/engine.js` — 補 `'relation-chain'` 與 `'personality-match'` 兩種 buildQuestion 分支
- `04_app/storage.js` — 加 `onboardingSeen` flag、`hintsUsed` 計數
- `04_app/styles.css` — reduce-motion media query block

**不動：**
- 03_graphrag/* 資料層
- 04_app/_archive/、04_app/三國演義探險地圖_v17.html

---

## Milestone 結構（4 個 sub-phase）

Phase 3 拆 4 個 milestone，每個 milestone 完一輪 codex dispatch + commit + browser smoke test，再進下一個。

```
3a：三主題視覺切換               (themes.css + router 改 + body class)
3b：剩 2 個題型                  (engine.js + stage.js + dnd.js + tests)
3c：友善設計 + 卡關保護          (safeguards.js + onboarding.js + celebrations.js)
3d：響應式手機 + 兒童 a11y       (styles.css media queries + 對比強化 + reduce-motion)
```

---

## Milestone 3a: 三主題視覺切換

### Goal
切到不同區塊時整體視覺主題明顯換場（地圖→竹簡 bamboo、舞台→沙盤 warroom、圖鑑→馬卡龍 classic）。

### Files
- Create: `04_app/themes.css`
- Modify: `04_app/index.html`（加 link）
- Modify: `04_app/router.js`（goto 時 set body.dataset.theme）
- Modify: `04_app/app.js`（init 時 default theme）

### Steps

- [ ] **3a-1: 寫 `04_app/themes.css`**

定義三組 CSS variable overrides，依 `body[data-theme="bamboo|warroom|classic"]` selector apply。對映表（依 interface spec § 2.3）：

```css
/* themes.css */
body[data-theme="bamboo"] {
  --color-bg: #F7F1E1; --color-surface: #FBF6E8;
  --color-text: #3F2D14; --color-text-soft: #8B6F4D;
  --color-primary: #7C5E2C; --color-primary-strong: #5A3F1C;
  --color-success: #5B8B4A; --color-danger: #A14E3A;
  --color-border: #D4C5A0;
  --color-faction-wei: #3F6F8E; --color-faction-shu: #A14E3A;
  --color-faction-wu: #5B8B4A; --color-faction-lords: #6B5D7E;
  --font-display: "Noto Serif TC", "Source Han Serif TC", serif;
}
body[data-theme="bamboo"] .top-bar { background: #FBF6E8; border-bottom-color: #D4C5A0; }
body[data-theme="bamboo"] .card { background: #FBF6E8;
  box-shadow: 0 1px 2px rgba(63,45,20,.1); border-color: #D4C5A0; }
body[data-theme="bamboo"] main { background: #F7F1E1; }

body[data-theme="warroom"] {
  --color-bg: #1E293B; --color-surface: #334155;
  --color-text: #F8FAFC; --color-text-soft: #94A3B8;
  --color-primary: #F59E0B; --color-primary-strong: #D97706;
  --color-success: #10B981; --color-danger: #EF4444;
  --color-border: #475569;
  --color-faction-wei: #60A5FA; --color-faction-shu: #FBBF24;
  --color-faction-wu: #34D399; --color-faction-lords: #C4B5FD;
}
body[data-theme="warroom"] .top-bar { background: #0F172A; border-bottom-color: #475569; }
body[data-theme="warroom"] .card { background: #334155;
  box-shadow: 0 2px 8px rgba(0,0,0,.4); border-color: #475569; color: var(--color-text); }
body[data-theme="warroom"] main {
  background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
  background-image: linear-gradient(rgba(255,255,255,.02) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.02) 1px, transparent 1px);
  background-size: 32px 32px;
}
body[data-theme="warroom"] .clue-card { background: #422006; color: #FDE68A; border-color: #92400E; }

body[data-theme="classic"] {
  /* 已是 styles.css 預設，這裡只 explicit 設一次方便切回 */
  --color-bg: #FFF7ED; --color-surface: #FFFFFF;
  --color-text: #1E293B; --color-text-soft: #64748B;
  --color-primary: #F97316; --color-primary-strong: #C2410C;
  --color-border: #E2E8F0;
  --color-faction-wei: #2563EB; --color-faction-shu: #F97316;
  --color-faction-wu: #16A34A; --color-faction-lords: #8B5CF6;
}
```

- [ ] **3a-2: index.html 加 link**

```html
<link rel="stylesheet" href="styles.css">
<link rel="stylesheet" href="themes.css">
<!-- 預設給 body 一個 data-theme -->
<body data-view="loading" data-theme="bamboo">
```

- [ ] **3a-3: router.js goto 加主題切換**

```javascript
const ROUTE_TO_THEME = { map: 'bamboo', stage: 'warroom', codex: 'classic' };
export function goto(route) {
  setState({ route, verdictOpen: null });
  document.body.dataset.view = route;
  document.body.dataset.theme = ROUTE_TO_THEME[route] || 'classic';
  // ...既有 tab toggle
}
```

- [ ] **3a-4: app.js init 設預設**

```javascript
document.body.dataset.theme = 'bamboo'; // 預設地圖主題
```

- [ ] **3a-5: Browser smoke test**：依序切三 tab、預期背景與卡片顏色明顯不同。

- [ ] **3a-6: Commit**

---

## Milestone 3b: 剩 2 個題型（relation-chain + personality-match）

### Goal
補 engine.js 與 stage.js 的兩種題型；node test 至少 +6 tests。

### Files
- Modify: `04_app/engine.js`（補兩個 buildQuestion 分支 + helper）
- Modify: `04_app/engine.test.js`（+6 tests）
- Modify: `04_app/views/stage.js`（UI 分支：relation-chain 顯示路徑 visualization、personality-match 顯示拖拉區）
- Create: `04_app/views/dnd.js`（拖拉互動）

### Steps

- [ ] **3b-1: engine.js 補 `'relation-chain'` builder**

題目：「{subject A}要找{subject B}說事，要經過誰最短？」
- 用 BFS 找 A → ? → B 最短路徑（限 2 跳）
- 正確答案：path 中間人
- 干擾項：3 個 A 認識的人但不在 path 上

```javascript
function buildRelationChainQuestion(subject, allNodes, rels, byId, profile) {
  // 找 subject 認識的另一個 character，他們之間有共同朋友 X
  // X 就是答案，干擾項是 subject 認識但不是 X 的人
  const subjectOutgoing = rels.filter(r => r.source === subject.id
    && r.target.startsWith('entity:character_'));
  if (subjectOutgoing.length < 4) return null;
  // 隨機選一個遠人 T (A→X→T pattern)
  // 邏輯：找跟 subject 透過一個中間人連到的人
  for (const candidate of shuffle(subjectOutgoing).slice(0, 10)) {
    const middleId = candidate.target;
    const middleNode = byId.get(middleId);
    if (!middleNode) continue;
    const middleOutgoing = rels.filter(r => r.source === middleId
      && r.target.startsWith('entity:character_')
      && r.target !== subject.id);
    if (middleOutgoing.length === 0) continue;
    const endNode = byId.get(shuffle(middleOutgoing)[0].target);
    if (!endNode) continue;
    // 干擾：subject 直接認識但非 middleNode 的 3 人
    const distractors = subjectOutgoing
      .filter(r => r.target !== middleId)
      .slice(0, 10)
      .map(r => byId.get(r.target))
      .filter(Boolean)
      .slice(0, 3);
    if (distractors.length < 3) continue;
    return {
      type: 'relation-chain', subject, edge: candidate,
      prompt: `「${subject.name}」想找「${endNode.name}」說事，要經過誰才認得？`,
      clue: `${subject.name} 跟 ${middleNode.name} ${candidate.relationType}；${middleNode.name} 跟 ${endNode.name} 也有交情。`,
      choices: shuffle([middleNode, ...distractors]),
      correctChoiceId: middleNode.id,
    };
  }
  return null;
}
```

- [ ] **3b-2: engine.js 補 `'personality-match'` builder**

題目：給 4 個個性敘述 + 4 個人物，拖拉配對。
- 從 personality.json 取 4 個 trait 不同的人物
- choices 為「敘述卡」，每張對應一個人物 id

```javascript
function buildPersonalityMatchQuestion(allNodes, personality, profile, pack) {
  // 從本包 chapter overlap 的 character 中挑 4 個有不同主 trait 的
  const candidates = allNodes.filter(n =>
    n.type === 'character' && n.isTrunk
    && chapterOverlap(n.chapters, pack)
    && personality[n.id]?.traits?.length > 0
  );
  if (candidates.length < 4) return null;
  // 取 4 個 traits 不重複的人
  const usedTraits = new Set();
  const picked = [];
  for (const n of shuffle(candidates)) {
    const t = personality[n.id].traits[0];
    if (!usedTraits.has(t)) {
      usedTraits.add(t);
      picked.push(n);
      if (picked.length === 4) break;
    }
  }
  if (picked.length < 4) return null;
  return {
    type: 'personality-match', subject: picked[0], edge: null,
    prompt: '把每個個性敘述拖到對應的人物身上',
    clue: '',
    // choices 為「敘述」，correctMap 是 trait→character_id
    choices: picked.map(n => ({
      id: n.id, name: n.name, traitLabel: personality[n.id].traits[0],
    })),
    correctChoiceId: 'matched', // 特殊：表示「全部對齊」才算對
    matchPairs: picked.map(n => ({ characterId: n.id, traitLabel: personality[n.id].traits[0] })),
  };
}
```

- [ ] **3b-3: engine.js 補 chooseQuestionType 邏輯**

升等：L2+ 觸發 relation-chain，L3+ 偶爾觸發 personality-match。

- [ ] **3b-4: engine.test.js 補 6 tests**

```javascript
test('buildQuestion relation-chain 結構正確', () => {
  const cao = nodes.find(n => n.name === '曹操' && n.type === 'character');
  const q = buildQuestion({ subject: cao, edge: null, allNodes: nodes, type: 'relation-chain', byId, rels, profile: EMPTY_PROFILE });
  if (q) {
    assert.equal(q.type, 'relation-chain');
    assert.equal(q.choices.length, 4);
    assert.ok(q.choices.find(c => c.id === q.correctChoiceId));
    assert.ok(q.prompt.includes(cao.name));
  }
});

test('buildQuestion personality-match 有 4 對配對', () => {
  // 載入 personality.json
  const personality = JSON.parse(readFileSync(`${REPO_ROOT}/03_graphrag/character_personality.json`));
  const q = buildQuestion({ subject: null, edge: null, allNodes: nodes, type: 'personality-match', byId, rels, profile: EMPTY_PROFILE, personality, pack: CHAPTER_PACKS[0] });
  if (q) {
    assert.equal(q.type, 'personality-match');
    assert.equal(q.matchPairs.length, 4);
    for (const p of q.matchPairs) {
      assert.ok(p.characterId);
      assert.ok(p.traitLabel);
    }
  }
});

// + 4 個更細的 test：relation-chain 中間人不為 subject 自己、
// personality-match 4 個 traits 不重複、distractor 都不在 path 上 等等
```

- [ ] **3b-5: views/stage.js 加題型分支**

依 `q.type` render 不同 UI：
- `relation-chain`：4 個 choice 顯示為 mini-path（A → choice → B），其他不變
- `personality-match`：4 張敘述卡 + 4 個人物頭像（無 choice grid），用 dnd.js 處理拖拉

- [ ] **3b-6: 寫 `04_app/views/dnd.js` 簡單 HTML5 drag-and-drop wrapper**

不引外部 lib，HTML5 native DnD：
```javascript
export function makeDraggable(el, onDrop) { /* dragstart / dragend */ }
export function makeDropZone(el, onDropped) { /* dragover / drop */ }
```

- [ ] **3b-7: node --test 確認新題型 tests pass、原 14 仍 pass**

- [ ] **3b-8: Browser smoke test**：在 ch001_010 包多次「換題目」直到看到 relation-chain（或在 ch011_020 包看 personality-match）。

- [ ] **3b-9: Commit**

---

## Milestone 3c: 友善設計（Onboarding + 卡關保護 + 慶祝）

### Goal
首次進站有 3 步引導；連錯有提示有保底；答對有彈跳 + toast；reduce-motion 全停動畫。

### Files
- Create: `04_app/views/onboarding.js`
- Create: `04_app/safeguards.js`
- Create: `04_app/views/celebrations.js`
- Modify: `04_app/storage.js`（加 `onboardingSeen` flag、`wrongStreak`）
- Modify: `04_app/views/stage.js`（整合 safeguards 與 celebrations）
- Modify: `04_app/app.js`（init 時 gate onboarding）

### Steps

- [ ] **3c-1: storage.js 加欄位**

```javascript
const DEFAULT = {
  unlockedPacks: ['ch001_010'],
  characters: {}, totalStars: 0,
  recentQuestions: [],
  onboardingSeen: false,
  wrongStreak: 0,
  hintsUsed: 0,
};
```

新增 `markOnboardingSeen(profile)`、`incWrongStreak(profile)`、`resetWrongStreak(profile)`。

- [ ] **3c-2: 寫 `views/onboarding.js`**

進站後若 `profile.onboardingSeen === false`，顯示三步浮層（spring slide-in，可跳過）：
1. 「歡迎來到三國世界 🏞」+ 指向地圖
2. 「點亮的關卡可以挑戰」+ 第一卡微跳
3. 「答對會學到人物的故事」+ 進度條閃光

每步「下一步」/「跳過」按鈕。完成或跳過後 `markOnboardingSeen()`。

- [ ] **3c-3: 寫 `safeguards.js`**

```javascript
export function shouldShowHint(profile) { return profile.wrongStreak >= 3; }
export function shouldForceAdvance(profile) { return profile.wrongStreak >= 5; }
export function applyAnswerOutcome(profile, correct) {
  if (correct) return { ...profile, wrongStreak: 0 };
  return { ...profile, wrongStreak: profile.wrongStreak + 1 };
}
```

stage.js submit 之後：先 record，再 applyAnswerOutcome；若 force-advance 顯示「沒關係，我們先過去 🌱」並自動 next。

- [ ] **3c-4: 寫 `views/celebrations.js`**

提供：
- `flashCardOnCorrect(targetEl)`：scale 1 → 1.08 → 1 spring
- `toastNewCharacter(name)`：頂部滑入「新人物：XX 加入圖鑑！」3 秒自動消
- `confettiOnMilestone()`：每 10 個解鎖時觸發（CSS animation 彩帶）
- 全部尊重 `prefers-reduced-motion: reduce` → 退化為 80ms fade

- [ ] **3c-5: stage.js submit 整合 safeguards + celebrations**

```javascript
const outcome = applyAnswerOutcome(updated, correct);
saveProfile(outcome);
if (correct && previousLevel < newLevel) {
  toastNewCharacter(subject.name);
}
if (shouldForceAdvance(outcome)) {
  showVerdict(mainEl, { correct: true, forced: true,
    explanation: '沒關係，這場我們先過去，回頭再來 🌱', ... });
} else if (!correct && shouldShowHint(outcome)) {
  // 在覆蓋層後 hint 模式：下次題目線索區顯示一條相關邊
  setState({ hintMode: true });
}
```

- [ ] **3c-6: app.js init gate onboarding**

```javascript
const profile = loadProfile();
if (!profile.onboardingSeen) {
  await showOnboarding();
}
```

- [ ] **3c-7: Browser smoke test**：
- 清 localStorage → reload → 看到 3 步引導
- 跳過 → reload 不再顯示
- 答錯 3 題 → 看到「想看一條提示嗎」提示
- 答錯 5 題 → 自動通關覆蓋層

- [ ] **3c-8: Commit**

---

## Milestone 3d: 響應式手機 + 兒童 a11y 強化

### Goal
375px viewport 任務舞台 2×2 候選格 + 底部固定 CTA + 拇指區優先；對比 ≥ 7:1；OS reduce-motion 全停動畫；字級切換生效。

### Files
- Modify: `04_app/styles.css`（補手機 media query block + reduce-motion block）
- Modify: `04_app/themes.css`（每主題的對比細調確認 AAA）
- Modify: `04_app/index.html`（加字級切換 segment control）
- Modify: `04_app/storage.js`（加 `fontScale: 'small'|'normal'|'large'`）
- Modify: `04_app/app.js`（init 設 root font-size）

### Steps

- [ ] **3d-1: styles.css 補手機 media query**

```css
@media (max-width: 767px) {
  .top-bar { flex-wrap: wrap; gap: var(--space-2); padding: var(--space-2); }
  .brand { font-size: 16px; flex: 1 0 100%; }
  .progress { max-width: none; }
  .view-tabs { flex: 1 0 100%; justify-content: center; }
  main { padding: var(--space-3); }
  .map-grid { grid-template-columns: 1fr; }
  .stage-question { font-size: 20px; padding: var(--space-4) var(--space-2); }
  .choices { grid-template-columns: repeat(2, 1fr); gap: var(--space-2); }
  .choice { min-height: 88px; padding: var(--space-3); }
  .stage-actions {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: var(--color-surface); padding: var(--space-3);
    border-top: 1px solid var(--color-border);
    /* 避開 home indicator */
    padding-bottom: max(var(--space-3), env(safe-area-inset-bottom));
  }
  main { padding-bottom: 88px; /* 留 stage-actions 高度 */ }
  .codex-grid { grid-template-columns: repeat(2, 1fr); }
}
```

- [ ] **3d-2: styles.css 補 reduce-motion**

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 80ms !important;
    transition-duration: 80ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

- [ ] **3d-3: index.html 加字級切換**

頂部 toolbar 增加 segment control：
```html
<div class="font-scale" role="group" aria-label="字級切換">
  <button data-scale="small">小</button>
  <button data-scale="normal" class="is-active">中</button>
  <button data-scale="large">大</button>
</div>
```

對應 CSS：`:root { --font-scale: 1; }` `html { font-size: calc(16px * var(--font-scale)); }`

- [ ] **3d-4: app.js 處理字級切換 + localStorage 記憶**

- [ ] **3d-5: 兒童 a11y 對比強化**

確認三主題的 `--color-text` ↔ `--color-surface` 對比 ≥ 7:1（AAA）。warroom 已是深色易達標；bamboo 與 classic 要驗證並可能微調 text 深一級。

- [ ] **3d-6: Browser smoke test 用 chrome devtools mobile preview**

- 切到 iPhone 12 mini (375px)
- 任務舞台 → 候選 2×2 → 底部固定動作條
- 圖鑑 → 兩欄卡片
- 切換主題後對比仍 ≥ 7

- [ ] **3d-7: Commit**

---

## Phase 3 完成檢查清單

- [ ] `themes.css` 三主題色票完成
- [ ] router.js 跳區塊時切 body.data-theme，顏色明顯不同
- [ ] engine.js + engine.test.js 含 `'relation-chain'` 與 `'personality-match'`，tests ≥ 20 pass
- [ ] views/dnd.js 拖拉 wrapper
- [ ] views/onboarding.js 3 步引導
- [ ] safeguards.js 連錯計數 + 提示模式 + 強制通關
- [ ] views/celebrations.js toast / 彈跳 / 彩帶 + 尊重 reduce-motion
- [ ] storage.js 含 onboardingSeen / wrongStreak / fontScale
- [ ] styles.css 手機 media query + reduce-motion block
- [ ] index.html 加字級切換
- [ ] 三主題對比皆 ≥ 7:1（AAA）
- [ ] git history 乾淨

## Phase 4 預告（不在本 plan，視需求決定是否做）

- 雲端同步 / 多人對戰 / 老師後台
- 在地圖上看人物關係連結圖（從覆蓋層展開全頁子圖）
- 章節原文閱讀整合（從 02_chapters/）
- 圖鑑分享圖卡（截圖傳朋友）
- 語音敘述（讀題）

完成 Phase 3 後，整站可定義為「一個能上線給孩子用的 v1.0」，可以正式 push 到 GitHub Pages。
