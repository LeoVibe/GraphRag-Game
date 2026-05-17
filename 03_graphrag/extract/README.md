# 03_graphrag/extract — LLM 抽取結果

每一回獨立用 LLM 抽出實體與關係的原始 JSON。

## 檔案

```
c001_graph.json ~ c060_graph.json   (共 60 個)
```

每檔對應一個章節，包含：

```json
{
  "chapter_no": 1,
  "entities": [
    {"id":"char_cao_cao", "name":"曹操", "type":"character", "aliases":[...]},
    ...
  ],
  "relations": [
    {"source":"char_cao_cao", "target":"char_liu_bei", "type":"...", "category":"..."},
    ...
  ]
}
```

## 萃取方式

- **模型**：Codex CLI 上跑的 GPT-5.5
- **粒度**：每章獨立呼叫一次（不跨章）
- **Prompt**：客製的「三國演義專用實體/關係抽取」prompt
- **批次**：分兩批執行（c001-c003 試驗批 + c004-c060 主批）

## 為什麼分章獨立

- 控制單次呼叫的 token 預算
- 失敗時只需重跑該章
- 同一實體在不同章被抽出時，章節資訊自然就保留下來，後續 merge 階段才做去重

## 下一步

這 60 個 JSON 經過 `merge_sanguo_graph.py` + `merge_sanguo_block_graphs.py` 兩階段合併，產生 `../unified/` 內的最終圖譜。

對應流程：`../../05_pipeline/02_extraction.md`、`../../05_pipeline/03_merge.md`
