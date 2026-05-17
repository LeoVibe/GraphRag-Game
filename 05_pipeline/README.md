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
