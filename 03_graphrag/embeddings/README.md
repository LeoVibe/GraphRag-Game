# 03_graphrag/embeddings — 向量化結果

把 452 個 chunk 用本地 `embeddinggemma:300m` 模型轉成向量。

## 檔案

| 檔案 | 用途 | 大小 |
|---|---|---|
| `embeddings.parquet` | 主檔（chunk metadata + text + vector）| 4.2 M |
| `embedding_manifest.jsonl` | 只含 metadata（無 vector），快速索引用 | 181 K |
| `summary.json` | 統計（chunk 數、模型、總時間）| <1 K |

## 規格

- **模型**：`embeddinggemma:300m`（本地 Ollama）
- **維度**：768
- **Chunk 數**：452
- **每 chunk 元素**：`chunk_id, chapter_no, text, vector[768]`

## 怎麼用

### Python + pandas
```python
import pandas as pd
df = pd.read_parquet("embeddings.parquet")
print(df.columns)  # chunk_id, chapter_no, text, vector
```

### Python + 向量檢索
```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 載入
df = pd.read_parquet("embeddings.parquet")
vecs = np.stack(df["vector"].values)

# 對你的 query 向量做檢索（需自己先把 query 用同模型 embed）
sims = cosine_similarity([query_vec], vecs)[0]
top5 = df.iloc[sims.argsort()[-5:][::-1]]
```

## 為什麼選 embeddinggemma-300m

- 本地可跑（隱私）
- 對中文（包含文言文）表現不錯
- 768 維是性能/容量平衡點

對應流程：`../../05_pipeline/04_embedding.md`
