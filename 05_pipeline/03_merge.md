# ③ 兩階段合併（Merge）

把 60 章獨立抽出的圖譜，去重 + 統一 → 全書 unified graph。

## 程式

- `scripts/merge_sanguo_graph.py`（章 → 區塊）
- `scripts/merge_sanguo_block_graphs.py`（區塊 → 全書）

## 兩階段流程

```
60 個 c0XX_graph.json
       │
       ▼   merge_sanguo_graph.py
6 個區塊（每 10 章一個）
  block_001_010 / block_011_020 / ... / block_051_060
       │
       ▼   merge_sanguo_block_graphs.py
03_graphrag/unified/
  ├── unified_entities.jsonl        (2663 實體)
  ├── unified_relationships.jsonl   (5049 關係)
  └── merge_*.jsonl + merge_summary.json
```

## 為什麼分兩階段而不是一次合掉

直接 60→1 合併在「同人物的別名比對」上會爆炸（n² 比對）。

分階段：
1. 章→區塊：規模小，可比較嚴格地比對別名
2. 區塊→全書：每個 input 已經是區塊內去重過的，總量少很多

## 合併邏輯

### 實體合併
- **同 type + 同 canonical name** → 直接合
- **同 type + 名字相似 + 別名重疊** → 提示合併（merge_decisions.jsonl 紀錄）
- **不同 type** → 不合，但記錄到 `cross_type_name_candidates.jsonl` 供人工審

### 關係合併
- 依「source / target / type」三元組分組
- 同組多筆 → 合一筆，章節列表 union
- `weight` = 該關係在原文出現次數

## 輸出檔案說明

| 檔案 | 用途 |
|---|---|
| `unified_entities.jsonl` | 最終實體（給網頁用）|
| `unified_relationships.jsonl` | 最終關係（給網頁用）|
| `block_entity_to_global.jsonl` | 區塊 ID → 全書 ID 對照（供 traceback）|
| `merge_decisions.jsonl` | 每次合併的決定紀錄 |
| `merge_reasons.jsonl` | 合併原因（哪些別名 / 哪些 evidence 觸發）|
| `cross_type_name_candidates.jsonl` | 跨 type 同名的候選（供人工檢視）|
| `dropped_relationships.jsonl` | 因兩端實體沒合上而被丟掉的關係 |
| `merge_summary.json` | 整體統計快照 |

## 重跑

```bash
# 階段 1
python scripts/merge_sanguo_graph.py --input 03_graphrag/extract --out blocks/

# 階段 2
python scripts/merge_sanguo_block_graphs.py --input blocks --out 03_graphrag/unified
```

## 品質指標（本次跑出）

- 入：3,465 個區塊實體 → 出：2,663 個全書實體（去重 802 個）
- 入：5,181 個區塊關係 → 出：5,049 條全書關係（去重 87 條）
- 丟棄：45 條（兩端實體沒對上）
