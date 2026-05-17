# GraphRag-Game · 三國演義探險地圖

把《三國演義》原文，用 GraphRAG 萃取成可探索的知識圖譜，再做成兒童友善的互動網頁。

🌍 **線上版**：https://leovibe.github.io/GraphRag-Game/

[![三國演義探險地圖](docs/images/cover.png)](https://leovibe.github.io/GraphRag-Game/)

## 內容（5 大區塊）

| 區塊 | 內容 | 大小 |
|---|---|---|
| `01_source/` | 原始全文（壓縮）| 666 K |
| `02_chapters/` | 章節切分後的 .md（120 個）| 1.7 M |
| `03_graphrag/` | 萃取 + 合併 + 向量化的完整結果 | 14 M |
| `04_app/` | 最終互動網頁（單檔可分享）| 3.3 M |
| `05_pipeline/` | 從原文到網頁的完整流程說明與程式 | 240 K |

總計約 **20 MB**。

## 資料規模

- 60 回原文 → 120 個章節檔（每回約 2 個 chunk）→ 452 個更小 chunk
- 萃取出 **2,663 個實體**（人物、勢力、戰役、地點、策略）
- **5,049 條關係**（軍事衝突、陣營統率、謀略、親族、地點、官職、故事連結）
- **452 個向量**（768 維，embeddinggemma-300m 本地模型）

## 技術棧

- **LLM 萃取**：Codex CLI + GPT-5.5（每章一次萃取）
- **向量化**：本地 Ollama + `embeddinggemma:300m`
- **GraphRAG**：Microsoft GraphRAG 3.0.9 設定相容（`03_graphrag/settings.yaml`）
- **網頁**：純 D3.js v7 + 單檔 HTML（無需後端、無需安裝）

## 怎麼使用

### 想直接玩網頁
打開 `04_app/三國演義探險地圖.html`，或上面的線上版連結。

### 想用這份資料做自己的應用
- 圖譜原始檔：`03_graphrag/unified/unified_entities.jsonl` + `unified_relationships.jsonl`
- 向量檔：`03_graphrag/embeddings/embeddings.parquet`
- 章節原文：`02_chapters/c001.md ~ c120.md`

### 想完整重跑這個流程
看 `05_pipeline/README.md`，五個步驟對照五個程式。

## 授權

資料部分：《三國演義》原文為公共領域。

程式與互動網頁：MIT License。
