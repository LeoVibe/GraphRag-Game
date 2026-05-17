# ② LLM 抽取（Extraction）

每章節獨立呼叫 LLM，抽出實體 + 關係。

## 程式

`scripts/codex_extract_sanguo_graph_first3.py`

## 輸入 → 輸出

```
02_chapters/c001.md ~ c120.md
       │
       ▼   每章呼叫 Codex CLI 一次
03_graphrag/extract/c001_graph.json ~ c060_graph.json
```

> 注：每個 `c0XX_graph.json` 對應一回（合併該回上半 + 下半的抽取結果）。

## 萃取 schema

```json
{
  "chapter_no": 1,
  "entities": [
    {
      "id": "char_cao_cao",
      "name": "曹操",
      "type": "character",       // character / faction / army / battle / event / strategy / location / object / title
      "aliases": ["孟德", "曹操"],
      "description": "..."
    }
  ],
  "relations": [
    {
      "source": "char_cao_cao",
      "target": "char_liu_bei",
      "type": "結拜",
      "category": "kinship",     // military / command / strategy / kinship / place / office / object / story / other
      "evidence": "原文片段..."
    }
  ]
}
```

## 為什麼用 Codex CLI

- 已內建 GPT-5.5 高品質模型
- 支援自定 prompt + JSON 模式
- CLI 形式好做 batch 處理
- 可以換成任何 OpenAI 相容 API（含本地 Ollama）

## 為什麼分兩批

| 批 | 章節 | 目的 |
|---|---|---|
| first3 | 1-3 回 | 試驗批，先驗證 prompt 與 schema |
| ch004-ch060 | 4-60 回 | 主批，固定 schema 跑滿剩餘 |

第一批用來抓 prompt 上的 bug（例如別名抓不全、type 分類錯）。

## 失敗處理

每章獨立 → 任一章失敗只需重跑那一章，不影響其他。

```bash
# 重跑單章
python scripts/codex_extract_sanguo_graph_first3.py --chapter 25
```

## Prompt 位置

`03_graphrag/prompts/extract_graph.txt` 是 GraphRAG 預設 prompt 的客製版。
