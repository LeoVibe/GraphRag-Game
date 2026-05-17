# ⑤ 網頁產生器（App Build）

把 unified graph + embedding 資料 → 兒童版互動探險網頁（單檔 HTML）。

## 程式

`scripts/generate_sanguo_adventure_map_v11.py`

## 輸入 → 輸出

```
03_graphrag/unified/unified_entities.jsonl
03_graphrag/unified/unified_relationships.jsonl
       │
       ▼   generate_sanguo_adventure_map_v11.py
04_app/三國演義探險地圖.html   (3.3 MB 單檔)
```

## 為什麼是單檔 HTML

- **零依賴**：不用 Node、不用 server，雙擊就開
- **可分享**：丟到 GitHub Pages、Dropbox、學校共用槽都能直接看
- **可離線**：D3 是 CDN，但內容資料全嵌入

## 內含

- D3.js v7（CDN）
- 全部 unified graph 資料（JSON 直接嵌入 `<script type="application/json">`）
- 兒童版介面樣板（HTML + CSS + JS 共 ~30 KB 程式碼）

## 介面四模式

| 模式 | 互動 |
|---|---|
| 👤 認識人物 | 點人 → 看其戰友 / 敵人 / 主公 / 親人 / 參與戰役 |
| ⚔️ 看大戰役 | 點戰役 → 看雙方參戰名單與結果 |
| 🏯 看國家 | 點蜀/魏/吳 → 看主君、武將、戰役、外交 |
| 🔗 找關係 | 兩個人名 → BFS 找最短關係鏈 |

## GraphRAG 特性的利用

| GraphRAG 欄位 | 怎麼用 |
|---|---|
| `relationType`（動詞）| 做關係子分類：斬殺/結拜/獻計... |
| `description`（原文）| 點關係卡片 → 顯示「📖 書中是這樣寫的：...」|
| `category` × 方向 | 區分主動/被動：殺人 vs 被殺 |
| `chapters` + `weight` | 章節脈絡 + 頻率 |

## 重跑

```bash
python scripts/generate_sanguo_adventure_map_v11.py \
  --entities 03_graphrag/unified/unified_entities.jsonl \
  --relations 03_graphrag/unified/unified_relationships.jsonl \
  --out 04_app/三國演義探險地圖.html
```

## 改動方向

- 修改 `CHAR_DATA` 字典：補更多角色的兒童版介紹
- 修改 `classifyRel()` 函數：調整關係子分類規則
- 修改 CSS variables：換配色（目前為馬卡龍色系）

直接編輯 `.py` 重跑，產出新 HTML 即可。
