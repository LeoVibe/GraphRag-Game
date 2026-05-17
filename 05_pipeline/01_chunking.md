# ① 章節切分（Chunking）

把《三國演義》原文 → 120 個 chapter chunks + 452 個更細的 sub-chunks。

## 程式

`scripts/prepare_sanguo_chaptered.py`

## 輸入 → 輸出

```
01_source/三國演義.md.zip   (原文壓縮)
       │
       ▼
02_chapters/c001.md ~ c120.md       (粗粒度：每回兩段)
        + 內部 chunks_txt/ (細粒度：452 個小塊，給 embedding 用)
```

## 切分邏輯

### 一級切分：依 `第 N 回` 標題

正則：`^第[一二三四五六七八九十百零]+回`

切出 60 個原始章節。

### 二級切分：每回分兩段（給 LLM 萃取用）

每回按字數中點，找最近的段落結尾切。理由：
- 整回送 LLM 容易超 token
- 但又不能切太細，避免事件被切斷

→ 產出 `c001.md ~ c120.md` 共 120 個檔。

### 三級切分：固定字數切塊（給向量化用）

每塊約 ~500 中文字、~25% overlap。產出 `sanguo_chaptered_c0XX_kYYYY.txt` 共 452 個。

→ 不在 repo 中，但每個塊都會在 embedding manifest 看到對應 metadata。

## 設計權衡

| 決策 | 原因 |
|---|---|
| 不用通用 splitter | GraphRAG 自帶的切分對中文章回支援差 |
| 自寫正則切回目 | 三國回目格式穩定且唯一 |
| 章節 frontmatter 保留書名/回數 | 後續所有處理都能反查回到原文 |

## 重跑

```bash
python scripts/prepare_sanguo_chaptered.py \
  --input 01_source/三國演義.md.zip \
  --out-chapters 02_chapters \
  --out-chunks chunks_txt
```
