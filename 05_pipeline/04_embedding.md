# ④ 向量化（Embedding）

把章節 chunks 用本地 embedding 模型轉成 768 維向量。

## 程式

`scripts/embed_sanguo_chaptered.py`

## 輸入 → 輸出

```
chunks_txt/sanguo_chaptered_c0XX_kYYYY.txt   (452 個小塊)
       │
       ▼   呼叫 Ollama embedding API
03_graphrag/embeddings/
  ├── embeddings.parquet           (主檔，含 vector)
  ├── embedding_manifest.jsonl     (只 metadata)
  └── summary.json                 (統計)
```

## 模型

- **名稱**：`embeddinggemma:300m`
- **維度**：768
- **執行**：本地 Ollama (`http://127.0.0.1:11434`)

## 為什麼選這顆

| 考量 | 為什麼 |
|---|---|
| 本地可跑 | 不必把原文傳到雲端 |
| 中文支援 | gemma 系列對中文（含文言）覆蓋好 |
| 300M 參數 | 桌機可以即時跑，速度可接受 |
| 768 維 | 與多數 retrieval 工具相容 |

## Schema

`embeddings.parquet` 每列：

| 欄位 | 型別 | 範例 |
|---|---|---|
| `chunk_id` | str | `c001_k0001` |
| `chapter_no` | int | 1 |
| `chunk_index` | int | 1 |
| `text` | str | "話說天下大勢，分久必合……" |
| `vector` | list[float, 768] | [0.012, -0.034, ...] |
| `token_count` | int | 487 |

## 增量機制

- 程式自動跳過已 embed 過的 chunk
- 中斷可續跑，看 checkpoint 即可
- 本次：316 個新 chunk + 136 個既有 → 共 452

## 重跑

```bash
# 先啟動 Ollama 並 pull 模型
ollama pull embeddinggemma:300m

# 跑 embedding
python scripts/embed_sanguo_chaptered.py \
  --input chunks_txt \
  --out 03_graphrag/embeddings \
  --model embeddinggemma:300m
```

## 怎麼用

```python
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

df = pd.read_parquet("03_graphrag/embeddings/embeddings.parquet")
vecs = np.stack(df["vector"].values)

# 對 query embed 後比對
sims = cosine_similarity([query_vec], vecs)[0]
top5 = df.iloc[sims.argsort()[-5:][::-1]][["chunk_id","chapter_no","text"]]
```
