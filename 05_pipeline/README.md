# 05_pipeline — 從原文到網頁的完整流程

```
原文 (01_source)
   │
   ▼  ① 章節切分
02_chapters/ (120 個 .md)
   │
   ▼  ② LLM 抽取（每章一次）
03_graphrag/extract/ (60 個 *_graph.json)
   │
   ▼  ③ 兩階段合併（章→區塊→全書）
03_graphrag/unified/ (unified_entities + unified_relationships)
   │
   ├──▼ ④ 向量化（chunks 切細後 embed）
   │   03_graphrag/embeddings/ (embeddings.parquet)
   │
   ▼  ⑤ 網頁產生器（讀 unified + embeddings）
04_app/三國演義探險地圖.html
```

## 五個步驟對照五個程式

| 步驟 | 說明文件 | 程式 |
|---|---|---|
| ① 切分 | [`01_chunking.md`](01_chunking.md) | `scripts/prepare_sanguo_chaptered.py` |
| ② 抽取 | [`02_extraction.md`](02_extraction.md) | `scripts/codex_extract_sanguo_graph_first3.py` |
| ③ 合併 | [`03_merge.md`](03_merge.md) | `scripts/merge_sanguo_graph.py` + `merge_sanguo_block_graphs.py` |
| ④ 向量化 | [`04_embedding.md`](04_embedding.md) | `scripts/embed_sanguo_chaptered.py` |
| ⑤ 產網頁 | [`05_app_build.md`](05_app_build.md) | `scripts/generate_sanguo_adventure_map_v11.py` |

## 重跑完整流程的環境需求

- Python 3.11+
- Codex CLI（步驟 ② 需要，可以用其他 LLM 替代）
- Ollama + `embeddinggemma:300m` 模型（步驟 ④ 需要）
- `pip install`：`pandas`, `pyarrow`, `jsonlines`, `tqdm`, `ollama`

## 為什麼分成五步驟而不是一條 pipeline

- **可重入**：任一步驟失敗只重跑那一步
- **可替換**：例如想換 LLM、換 embedding 模型，只影響對應步驟
- **可檢查**：每步產出都是人類可讀的 JSON / Markdown，方便抽查品質
- **可分散**：抽取階段可以多開幾個 process 平行跑

---

## Phase 1 新增：v3 csv → 前端 JSON pipeline

跟上面的「原文 → 萃取」主 pipeline 並行，Phase 1 加了另一條從 GraphRAG v3
csv 變成前端可 fetch 的 JSON 的轉檔腳本。這個 pipeline 服務「人物圖鑑 ×
關係偵探」設計的資料層需求。

```
03_graphrag/sanguo_v3_nodes.csv          (從台科 neo4j v3 匯入)
03_graphrag/sanguo_v3_relationships.csv
   │
   ▼  build_graph.py
03_graphrag/nodes.json   (typed, prettified, 1534 筆)
03_graphrag/rels.json    (typed, prettified, 6615 筆)
   │
   ▼  precompute_questions.py
03_graphrag/character_personality.json   (287 位人物的 ratios + traits)
```

### 跑法

```bash
python3 05_pipeline/build_graph.py            # csv → nodes.json / rels.json
python3 05_pipeline/precompute_questions.py   # 預算個性比例
```

### 兩支腳本

| 檔案 | 輸入 | 輸出 |
|---|---|---|
| `build_graph.py` | `sanguo_v3_*.csv` | `nodes.json` / `rels.json` |
| `precompute_questions.py` | `nodes.json` `rels.json` | `character_personality.json` |

#### build_graph.py
- `;` 分隔字串轉成 int array（chapters）
- `|` 分隔字串轉成 string array（aliases）
- 數字欄位轉成 int / float、isTrunk 轉成 bool
- UTF-8 prettified（ensure_ascii=False）

#### precompute_questions.py
對每個 `kind=entity, type=character` 的人物：
- 統計 outgoing relationship 的 4 個 personality categories（strategy / command / military / kinship）的比例
- 套用閾值產出 traits（詳見 `docs/superpowers/specs/2026-05-23-sanguo-character-codex-design.md` § 6）

### 測試

```bash
python3 -m unittest discover -s 05_pipeline/tests -v
```

預期：15 tests (8 build_graph + 7 precompute) all PASS。需要 Python 3.9+，
無外部依賴。

### Phase 1 環境需求（比上面主 pipeline 簡單）

- Python 3.9+（macOS 系統內建即可）
- 無 pip 安裝需求
