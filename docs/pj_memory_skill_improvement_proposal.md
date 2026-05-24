# pj_memory Skill 改進 Proposal

`created`: 2026-05-24
`status`: proposal — 待 user ack 才動 `~/.claude/skills/pj_memory/`
`context`: 本專案 (GraphRag-Game) 第一次 distill 時，agent 寫出 5 條全是「執行歷程 / 技術細節 / 踩坑做法」的 candidate，被 user 指出方向錯誤。回頭檢視 Skill 引導為何會這樣。

---

## 一、問題：Skill 引導 agent 寫出錯誤的長期記憶

### 1.1 實例

第一次 distill 時，agent 寫出的 5 條 candidate：

| Candidate | 主題 | 問題 |
|---|---|---|
| A | 兒童視覺一致性 | 還算抽象，但描述方式偏 lesson 而非 dna |
| B | 真實 mockup 不要 ASCII | **「做法 / 設定」**而非「原則 / 抽象經驗」 |
| C | ES module `?v=N` invalidate | **完全是技術 cookbook**，該在 commit/code 註解 |
| D | codex 沒輸出自己做 | **工作流程細節**而非原則 |
| E | BFS minHops per-path visited | **完全是 debug 細節**，該在 commit message + code 註解 |

User 直接點出：「**這些是工作的歷程而不是整個專案的價值 ⋯ 這些都已經寫在環境配置檔案中不需要寫在長期記憶裡，反而長期記憶要寫的是去哪邊看這些設定**」。

### 1.2 Root cause 分析（為什麼 Skill 會這樣引導）

對照 `~/.claude/skills/pj_memory/references/spec.md` 與 `templates.md` 找到 3 個結構性問題：

**① 範例就是技術 cookbook**

`templates.md` §1 範例「用 Redux 管理全域狀態」：
- Distilled View 寫：「Redux 在 5+ 模組共享 state 時 OK；< 3 模組用 Context API」
- Applies When 寫：「模組數 < 3」「state 跨組件樹深度 < 4 層」
- Rejected Alternatives 列：「Redux Toolkit / Zustand / MobX」

這是**技術建議 cookbook**，看到範例後 agent 模仿同樣結構，自然寫成「ES module 用 ?v=N 解 cache」「BFS visited per-path」這類細節。

**② type 7 種沒有「該寫 vs 不該寫」對照**

`spec.md` §四列了 `insight / decision / lesson / dna / risk / open_question / pattern`，每個都附「例子」（如 pattern = 「每次 API 重構撞 type 不一致」），**沒有反例**。

agent 看到 `lesson` 定義「踩雷紀錄」+ 例子「混用 setState + useReducer race condition」，就會寫「BFS minHops 用 per-path visited」當 lesson — 沒人告訴他這該在 code comment 而不是長期記憶。

**③ 沒有 Pointer-only 型態 + 沒有「抽象→引導→行為改變」結構**

所有 type 預設 body 都要寫 Distilled View / Why It Matters / Evidence / Applies When / Do Not Apply When ⋯ 這些欄位**引導 agent 把細節塞進去**。

沒有：
- **Pointer-only type**：「遇到 X 類問題 → 去看 commit Y / file Z」
- **「抽象原則 + 引導性 + 行為改變」結構**：解釋未來怎麼判斷、因為這條改了什麼設計

`Success Criteria` 段有「可觀測未來行為改變」的精神，但**沒明示「Distilled View 必須是引導未來行為的抽象原則，不可含具體實作細節」**。

---

## 二、調整方向：長期記憶的本質

### 2.1 該寫 vs 不該寫對照表

| 該寫 | 不該寫（去 commit/code/spec） |
|---|---|
| **原則** — 跨情境的抽象判斷準則 | 具體 hex 色碼、port 號、API 參數 |
| **抽象經驗** — 從踩坑提煉的「下次怎麼判斷」| 踩坑時改的程式碼 |
| **Pointer** — 「遇到 X 類問題去看 commit Y / file Z」 | X 類問題的解決方案內容 |
| **DNA** — 這個專案的本質 / 價值 | 某次決定的具體參數 |
| **行為改變** — 因為這條，流程 / 設計改了什麼 | 流程細節怎麼跑（這在 SOP / scripts） |

### 2.2 「抽象經驗」的標準：必須有引導性 + 行為改變

User 明示：「**抽象經驗就是要有足夠的引導性，因為這個引導性就改了什麼樣的設計，而不是只有寫你做了什麼事情**」

每條長期記憶必須答出三個問題：

1. **抽象經驗**：這次體會到的「不變的事」是什麼？（跨情境）
2. **引導性**：未來遇到類似情境，怎麼用這條來判斷？
3. **行為改變**：因為這條，我們改了什麼設計 / 流程 / 判斷方式？

**對比示例：**

| 不合格寫法（做了什麼） | 合格寫法（抽象 + 引導 + 行為改變） |
|---|---|
| ASCII layout 對使用者沒辦法感受，必須給真實 HTML mockup screenshot | **抽象**：設計討論的瓶頸不是 idea 而是「表達載體」。<br>**引導**：進入「要不要做這個設計」前先檢查載體是否能讓對方視覺判斷；不能就先做 mockup 再回來談。<br>**行為改變**：設計討論流程從「列 4 ASCII 選項問選哪個」改為「先做 1 個推薦 HTML → 截圖 → 你回饋」。 |
| 改完 module 後加 ?v=2 強制 cache invalidate | **不該寫**。這是 commit message + code comment 該記的細節。<br>長期記憶該寫：「遇到 cache 問題 → 看 commit `adf3cef` 與 `04_app/v18/data.js` 註解」。 |

---

## 三、具體 Skill 改動建議

### 3.1 spec.md 改動

**§四 type 重新定義（精簡為 3 種）：**

| Type | 意思 | 何時用 | 反例（**不要寫成 type X**） |
|---|---|---|---|
| `dna` | 跨情境的價值 / 本質 / 準則 | 「兒童產品視覺一致性 > 技術展示」 | 「Redux > Context API」（技術選型不是 DNA）|
| `principle` | 從踩坑提煉的判斷準則（含引導性 + 行為改變）| 「設計討論瓶頸是表達載體 → 先給 mockup 再討論」 | 「ASCII 不夠用要給 HTML」（沒抽象出來）|
| `pointer` | 指向具體實作 / 解法的索引 | 「遇到 module cache 問題 → 看 commit Y」 | 「module cache 解法是 ?v=N」（這是答案不是 pointer）|

**廢除**：`insight` / `decision` / `lesson` / `risk` / `pattern` / `open_question` — 太容易裝細節，且 `dna+principle+pointer` 已涵蓋。

**§七 body 結構改為強制三段：**

```markdown
## 抽象原則         （≤ 80 字，跨情境的判斷準則）
## 引導性          （未來遇到類似情境怎麼用這條判斷？）
## 行為改變         （因為這條，我們改了什麼設計 / 流程？）
## Pointer         （技術細節在哪：commit / file / docs 路徑，列 ≤ 5 條）
```

**廢除**：原 `Distilled View / Why It Matters / Origin Story / Evidence / Applies When / Do Not Apply When / Rejected Alternatives / Tensions & Gaps` — 7 段過量、且 Origin / Applies / Rejected 都鼓勵寫細節。

**新增規則**：
- 抽象原則段**禁止**出現 hex 色碼、port 號、具體檔名、commit hash、程式碼片段
- 那些內容只能在 Pointer 段以「`commit abc123` — 一句說明」格式列出

### 3.2 templates.md 改動

刪除「用 Redux 管理全域狀態」範例（誤導），換成：

```markdown
---
type: principle
gravity: G3
title: "設計討論的瓶頸是表達載體不是 idea"
---

## 抽象原則
當對方說「沒辦法感受」，是溝通載體（ASCII / 文字 / 簡報）錯了，不是 idea 不夠好。再多文字解釋無法替代視覺示範。

## 引導性
進入「要不要做這個設計？」討論前，先自問三題：
1. 對方能用視覺直接判斷嗎？
2. 我有給對方對照組嗎？
3. 我把判斷成本丟給對方了嗎？
三題任一答 no → 先做 mockup 再回來。

## 行為改變
設計討論流程從「列 4 ASCII 選項問選哪個」改為「先做 1 個推薦 HTML → 截圖傳過去 → user OK/想調/否定」。前者把判斷成本丟使用者，後者留給自己。

## Pointer
- commit `57301c6` 本專案首次使用真實 HTML mockup（3 個 mode）
- `docs/mockups/` 三個 v2 mockup HTML
```

### 3.3 writing-discipline.md 新增 W9-W10

**W9 — 寫每條記憶前的「不該寫」檢查**：
- ❌ 含具體 hex / port / 程式碼 / 參數值 → 改寫 Pointer
- ❌ 描述「做了什麼步驟」→ 改寫「為什麼這個原則重要」
- ❌ 沒有「未來怎麼判斷」→ 抽出引導性
- ❌ 沒有「改了什麼設計」→ 抽出行為改變

**W10 — 「commit message / code comment 已經有了嗎？」三問**：
寫 candidate 前自問：
1. 這次的學習，commit message 已經寫了嗎？
2. code comment 已經寫了嗎？
3. README / spec / plan 已經寫了嗎？

三題任一答 yes → 改寫成 `type=pointer`，body 只指方向不重複內容。

### 3.4 SKILL.md 改動

範本 1 「Distill 選擇題」example 改成符合新 spec：

```
🗣 pj_memory → user:

  本 session 抓到 X 條候選（全部 [agent_proposed]）：

  [Candidate]
    type: principle | gravity: G3
    title: 「設計討論的瓶頸是表達載體不是 idea」

    抽象原則: 當對方說「沒辦法感受」，是載體錯了不是 idea 不夠好。
    引導性: 設計討論前先檢查載體 — 對方能用視覺判斷嗎？
    行為改變: 流程從「列 ASCII 選項」改為「先做 mockup screenshot」。
    Pointer: commit 57301c6, docs/mockups/

  你想:
    [a] 升 active
    [b] 升 active 但讓我改 type/gravity/原則 描述
    [c] 暫存 candidate, 下週再決定
    [d] 廢棄
```

---

## 四、變更影響評估

| 變更 | 影響 | Migration cost |
|---|---|---|
| type 7 → 3 | 既有 item 要 re-map：lesson → principle, decision → principle (有引導性) 或 pointer (純技術選擇), insight → principle, pattern → pointer (大多), risk → principle 或 open_question 留, open_question 留 | 中（人工 review 每條）|
| body 8 段 → 4 段 | 既有 item 要 re-write body | 中（人工 distill）|
| 範本範例換抽象原則 | 範本只 1 個檔，改完即生效 | 低 |
| W9-W10 紀律 | 純加新規則 | 低 |

**這個專案 (GraphRag-Game) 還沒寫任何 active item**，剛建 W1 結構。**正好可以 0-cost 開始用新 spec**，不必 migration。

---

## 五、Action items（等 user ack）

| Step | 動作 | Where |
|---|---|---|
| 1 | User review 本 proposal | `docs/pj_memory_skill_improvement_proposal.md` |
| 2 | User ack 後動 spec | `~/.claude/skills/pj_memory/references/spec.md` |
| 3 | 同步動 templates | `~/.claude/skills/pj_memory/references/templates.md` |
| 4 | 加 W9-W10 紀律 | `~/.claude/skills/pj_memory/references/writing-discipline.md` |
| 5 | 改 SKILL.md 範本 1 example | `~/.claude/skills/pj_memory/SKILL.md` |
| 6 | 重新 distill 本 session 的 C/D/E 用新 spec | `docs/project_memory/items/` |

---

## 六、Open Questions

- 是否要讓既有 7 type 跟新 3 type **並存一陣子**（讓既有專案不破壞），還是直接切換？
- `pointer` type 是否需要 anchor 強制驗證（commit hash / file path 真實存在）？
- 「抽象原則」的字數上限多少合適（80 字 / 120 字 / 不限）？
