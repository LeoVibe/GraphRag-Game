# 三國演義探險地圖：人物圖鑑 × 關係偵探 重構設計

版本代號：`sanguo-character-codex`
日期：2026-05-23
取代範圍：v15 / v16 / v17 / v18 既有的「戰役推理」與「人物探險」設計

---

## 1. 動機

V17/V18 的「戰役推理」面板存在三個無法靠微調修復的問題：

1. **資料層 bug**：`BATTLE_LESSON_PRESETS` 寫死 3 場戰役 × 4 步驟 = 12 段文字，渲染時對每個 focus 人物產出一張卡，但卡片內容共用同一段 `step.text`——使用者實測截圖中袁紹與曹操兩張卡顯示同樣的「袁紹與曹操爭奪北方主導權，官渡成為對決焦點。」
2. **互動 bug**：「在地圖上看」按鈕在 step.focus 對應人物未出現在當前章節時，`selectNode(undefined)` 靜默失敗，按了沒反應。
3. **設計 bug**：6615 條 relationship 沒被當題庫用，使用者把 GraphRAG 結構降階成靜態文字面板，無法支撐兒童「探索 → 推理 → 鞏固」的學習迴圈。

同時專案存在 **repo 分裂**：開發在 `testProject/台科課程實作/`（含 v18 build），發佈在 `testProject/GraphRag-Game/`（僅到 v17），GitHub 連動只認後者。

本 spec 同時解決以上問題。

## 2. 目標使用者與情境

- **年齡**：國小中高年級到國中（約 10–14 歲）
- **情境**：學生**自學**為主，沒有老師或家長從旁說明
- **學習目標**：**認識人物個性與關係網**（不是因果推理、不是視角扮演、不是寫死的知識傳遞）
- **節奏**：一輪學習循環 1–3 分鐘可走完，孩子可在零碎時間進站
- **內容範圍**：**三國演義前 60 回**（手頭原文僅 c001-c060）。涵蓋黃巾之亂、董卓進京、群雄逐鹿、官渡、赤壁、荊南西川。**不涵蓋**諸葛亮北伐、五丈原、姜維、鄧艾、鍾會等 61 回以後的戲份。因此司馬懿、姜維、鄧艾等後期人物在資料層 degree 極低，會在前端圖鑑被歸為「次要角色」而非「熟識目標」。

## 3. 終態總覽

整站對齊到「認識人物」三階段，使用者熟悉的遊戲語言：

```
頂部：我的圖鑑進度 ●●●●○○○○○○ 12/60 ★3

├── 主頁地圖     12 個事件包（按章節），亮 / 暗代表是否解鎖
├── 任務舞台     當前任務的偵探謎題 + 圖譜 + 解釋
└── 人物圖鑑     60 張人物卡，按認識度（★/★★/★★★/未遇見）排序
```

舊 mode → 新區塊對映：

| 舊 mode | 新區塊 | 兒童的話 |
|---|---|---|
| `mode: relation` | 主頁地圖 | 「世界地圖」 |
| `mode: battle`   | 任務舞台 | 「正在挑戰」 |
| `mode: person`   | 人物圖鑑 | 「我認識的人」 |

## 4. 核心學習循環

孩子每輪 5 個 phase：

1. **進場**——事件標題 + 一句情境（從 GraphRAG 章節摘要取）
2. **觀察**——事件相關的小型關係圖譜，新人物會以「？」狀態出現
3. **出題**——4 選 1 題目，含圖譜線索閃爍
4. **回饋**——
   - 答對：閃綠 → 顯示「為什麼對」（取 `relationship.description`）→ 人物卡升等動畫
   - 答錯：閃紅 → 標出正確答案位置 → 顯示「你選的這個其實是 OOO」→ 不扣分、可再試
5. **升級**——當前人物卡升一級、解鎖一條新關係邊、進度條 +1

連錯 3 題啟動**提示模式**（題目下顯示一條相關邊）；連錯 5 題**自動通關**避免卡住。

## 5. 五種題型

依認識深度漸進：

| 題型 | 範例 | 用到的 GraphRAG 欄位 | 深度 |
|---|---|---|---|
| 誰是誰 | 「下面誰最常跟著劉備？」（4 候選頭像） | `entity.description`, 共同章節 | L1 |
| 他們什麼關係 | 「劉備跟關羽是？」（兄弟 / 主臣 / 對戰 / 計策） | `relationship.category` | L1 |
| 誰是同夥 | 「下面 4 人，3 個是曹魏，誰不是？」 | `node.camp` + community detection | L2 |
| 關係鏈 | 「諸葛亮要傳話給孫權，最短路徑要經過誰？」 | 多跳 path-finding | L3 |
| 個性配對 | 4 個個性敘述 ↔ 4 個人物（拖拉） | 統計人物所有 relationship.category 比例自動生成 | L4 |

## 6. GraphRAG 出題引擎

**資料金礦**（從 `03_graphrag/extract/c001-c060_graph.json` 經 `merge_extracts.py` 合併產出，**取代** v3 csv 與 unified jsonl 兩個有 bug 的中間產物——詳見 `docs/superpowers/plans/2026-05-23-sanguo-codex-phase1-data-fix.md`）：

| 欄位 | 用途 |
|---|---|
| `relationship.description` | 直接當題幹 / 解釋（已是兒童句，用 `；` 分多句） |
| `relationship.category` | 9 類 → 「他們什麼關係」答案集 |
| `node.chapters` | 章節包過濾，避免出當前包還沒出現的人物 |
| `node.aliases` | 進階題材料（「孟德、阿瞞、曹公都是誰？」） |
| `node.degree` + `score` | 解鎖優先序：先教 degree 高的 |
| `node.camp` | 干擾項挑選 |
| `node.isTrunk` | 666 主幹節點必考 |

**生題函式骨架：**

```js
generateQuestion(currentPack, learnerProfile) {
  const candidates = nodes.filter(n =>
    n.kind === 'entity' && n.type === 'character' && n.isTrunk
    && hasChapterOverlap(n.chapters, currentPack.chapterRange)
    && !learnerProfile.recentlyTested(n.id, lastNTurns = 5)
  );
  const subject = weightedPick(candidates, unfamiliarityWeight);
  const edge = pickEdge(subject, currentPack, learnerProfile);
  const type = chooseQuestionType(learnerProfile.level);
  const distractors = pickDistractors(edge);  // 同 camp、不同 relationType
  return buildQuestion({ subject, edge, type, distractors });
}
```

**干擾項策略**：3 個跟正確答案同 camp 但不同 relationType 的人物（degree 由高到低）——這是孩子最容易混淆的選項。

**個性配對題**（L4）特別：
- 統計人物 X 所有 outgoing relationship 中**屬於 4 個 personality categories 的比例**（分母為 strategy/command/military/kinship 之和而非全部 9 類——這樣 traits 才會在實際資料 fire，story/other 比例太大會稀釋）
- 對應到敘述。閾值：`strategy ≥ 20%` → 「會算計」；`command ≥ 25%` → 「會帶人」；`military ≥ 30%` → 「會打仗」；`kinship ≥ 10%` → 「重感情」
- 4 個人物各算一組敘述，孩子拖拉配對

## 7. 進度資料模型

單機 `localStorage`，不需後端：

```js
{
  unlockedPacks: ['ch001_010', 'ch011_020'],
  characters: {
    '曹操': {
      level: 3,                  // 0=未遇見, 1=聽過, 2=認識, 3=熟識
      lastSeen: timestamp,
      correctAnswers: 8,
      wrongAnswers: 1,
      discoveredRelations: [edgeId, ...]
    }
  },
  totalStars: 12,
  recentQuestions: [...]         // 防呆：最近 20 題不重出
}
```

升級條件（初版，plan 階段可調）：每 3 次正確答題且涵蓋該人物 ≥ 2 種題型 → 升一級；連續 2 次答錯回退 0.5 級（不低於初始 1）。

## 8. 部署架構與檔案重整

**最終只留 `GraphRag-Game/`**（GitHub 連動），`台科課程實作/` 需要的檔案搬進來：

```
GraphRag-Game/
├── 01_source/                       小說原文（保留現有）
├── 02_chapters/                     章節 markdown（保留現有）
├── 03_graphrag/
│   ├── sanguo_v3_nodes.csv          ← 從台科搬
│   ├── sanguo_v3_relationships.csv  ← 從台科搬
│   ├── metadata.json                ← 從台科搬
│   ├── nodes.json                   ← 新：拆給前端 fetch
│   └── rels.json                    ← 新：拆給前端 fetch
├── 04_app/
│   ├── index.html                   ← 薄殼 + 動態載入
│   ├── app.js                       ← 主邏輯（地圖 / 任務舞台 / 圖鑑切換）
│   ├── engine.js                    ← 題目生成引擎
│   ├── styles.css                   ← 拆出（沿用 v17 sanguo visual style 色票）
│   └── _archive/                    舊版 v15/v16/v17 移進來保存
├── 05_pipeline/                     建檔流程
│   ├── build_graph.py               ← 從台科搬精選（csv → nodes.json / rels.json）
│   ├── precompute_questions.py      ← 新：預算個性比例 / 干擾項候選表
│   └── requirements.txt
├── docs/
│   ├── superpowers/specs/2026-05-23-sanguo-character-codex-design.md  本文件
│   ├── spec_sanguo_v14 ~ v17.md     保留歷史
│   └── DESIGN.md                    新：整體設計總綱（萃取本 spec 給 PM 看的版）
├── README.md                        改：source → pipeline → app 三層說明
└── index.html                       根目錄首頁（保留作轉址）
```

**資料外掛化**（最大改動）：

舊（3.9 MB 單檔）：
```html
<script id="graph-data">{"nodes":[...1534...],"relationships":[...6615...]}</script>
```

新（fetch JSON）：
```html
<script>
  fetch('../03_graphrag/nodes.json')
    .then(r => r.json())
    .then(nodes => { /* ... */ });
</script>
```

**遷移範圍**：
- `台科課程實作/graphrag-sanguo/sanguo_neo4j_v3/import/*.csv` + `metadata.json` → `03_graphrag/`
- `台科課程實作/scripts/generate_sanguo_adventure_map_v18.py` → `05_pipeline/build_html.py`（重構）
- `04_app/三國演義探險地圖_v15/v16/v17.html` 與 `.htm` → `04_app/_archive/`
- 根目錄 `三國演義探險地圖.html` → 改為轉址到 `04_app/index.html`（保留舊 URL）

## 9. 從現況遷移

| 保留 | 取代 | 刪除 |
|---|---|---|
| sanguo visual style 色票、字型、icon | v17 戰役推理面板 → 任務舞台 | `BATTLE_LESSON_PRESETS` 三場寫死戰役 |
| 60 章 markdown 與 GraphRAG 圖譜資料 | v17 人物探險 → 圖鑑頁 | 3.9 MB 單 HTML（拆成 4 個檔） |
| 根目錄首頁 URL 不變 | v17 路徑學習 → 主頁世界地圖 | 寫死的 4 步推理板 UI |

## 10. 驗證

| 項目 | 方法 |
|---|---|
| 截圖那個 bug 消失 | 5 個章節包各出 3 題，每題 4 候選文字應全不同（puppeteer 截圖比對） |
| 「在地圖上看」可動作 | 10 個解釋頁各點一次，全頁切到圖譜 sub-view 且 edge 高亮 |
| 不出超出章節範圍人物 | 包 1（1-10 回）出 20 題，所有候選的 `chapterStart ≤ 10` |
| 干擾項合理 | 隨機 50 題抽查，干擾項都在同 camp 但不同 relationType |
| 進度持久化 | 答 5 題、reload、繼續答 → localStorage 留 5 題紀錄與解鎖狀態 |
| 60 章載入速度 | Lighthouse FCP < 2s（首頁只載 metadata.json） |

## 11. 錯誤處理

| 情境 | 處理 |
|---|---|
| 章節包內可考人物 < 5 | 自動降階：出簡單「誰是誰」題；湊不出 5 題直接「本包學習完成」 |
| `relationship.description` 空 | fallback：`{from} — {category_label} — {to}` |
| 連錯 3 題 | 啟動提示模式：題目下顯示 1 條相關邊 |
| 連錯 5 題 | 自動通關，不卡住 |
| `localStorage` 滿 | 只留最近 50 題 + 解鎖狀態，溢出砍最舊 |
| 抽不出 4 個同 camp 干擾項 | 容許跨 camp，但顯示「進階題」標籤 |

## 12. 明確不做的事（YAGNI）

| 不做 | 理由 |
|---|---|
| 後端 / 帳號 / 雲端同步 | 自學情境，localStorage 足夠 |
| 多語言 | 目標群是中文兒童 |
| 在線 LLM 即時生題 | 6615 條 `relationship.description` 已是現成題庫 |
| 老師後台 / 課堂管理 | 使用者選「自學」情境 |
| 保留 `BATTLE_LESSON_PRESETS` 作 fallback | 兩套邏輯難維護，完全刪除 |
| 角色語音 / 動畫 | 聚焦推理機制與圖鑑收集，動畫留待後續 |
| 改動 sanguo visual style 色票 / 字型 | 視覺資產保留，只重構版面結構 |

## 13. 後續可選（不在本 spec）

- 多人對戰模式（兩人比答題）
- 老師後台 / 課堂模式
- 章節原文閱讀 hint（「看原文」按鈕）
- 圖鑑分享圖卡（截圖傳朋友）
- 語音敘述（讀題給低年級孩子聽）
- 跨裝置雲端同步

## 14. 已決議的設計選擇

| 議題 | 決議 | 理由 |
|---|---|---|
| 整體方向 | 方案 A：人物圖鑑 × 關係偵探 | 動態利用 GraphRAG、自學進階明確、bug 自然消失 |
| 三大區塊 | 主頁地圖 / 任務舞台 / 人物圖鑑 | 對齊「認識」三階段、孩子熟悉的遊戲語言 |
| 題型數量 | 5 種全保留 | 對應認識深度 L1–L4 漸進 |
| 進度儲存 | localStorage | 自學情境不需後端 |
| repo 整併 | 全拆 + 舊版歸檔 + 台科同步進 GraphRag-Game | 「最後只留 GraphRag-Game」是使用者明訂約束 |

---

## 15. 介面細節（外連）

本 spec 聚焦「整站結構 + 出題引擎 + 資料模型 + 部署架構」。視覺、互動、響應式、a11y 等介面層細節另寫於：

- `docs/superpowers/specs/2026-05-23-sanguo-character-codex-interface-spec.md`

介面 spec 涵蓋：三主題對應三區塊、Design Tokens、桌面 / 手機 mockup、四題型 UI 差異、響應式 breakpoint、兒童 a11y 特別條款、友善設計與卡關保護機制。

---

附：對應的 implementation plan 將由 superpowers writing-plans skill 在主 spec + interface spec 都被使用者 review 後一併產生。
