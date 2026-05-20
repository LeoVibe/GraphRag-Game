# Spec: 三國演義探險地圖 V15 人物探險版位重整

## Objective

V15 重新整理 `人物探險` 的學習流程。目標使用者是國小中高年級學生；畫面要讓孩子先選人物，再看關係圖，接著用分類標籤閱讀關係人物，最後在右側補充人物資料、重要時刻與書中脈絡。

V14 的問題是：左側同時放起點人物、關係類型、陣營、搜尋，右側又顯示關係分類，下方再放人物資訊與重要時刻。資訊分散，孩子不容易知道「現在要先看哪裡」。

## Core Flow

人物探險的閱讀順序固定為：

1. 選人物：從三位主角或搜尋開始。
2. 看地圖：觀察目前人物與周圍人物/事件的關係。
3. 讀關係人物：在中央下方用標籤切換不同關係類型。
4. 補脈絡：右側閱讀人物檔案、關鍵時刻與歷史本記。

## Layout

### Left: 選人入口

左側只處理「我要看誰」：

- `三位起點`：劉備、曹操、孫權。
- `搜尋英雄`：直接輸入人物名。
- `選擇英雄`：四個陣營篩選按鈕，只有 `魏 / 蜀 / 吳 / 其他`。

陣營按鈕規則：

- 單一選擇。
- 再點已選按鈕即可取消。
- 沒有任何陣營選中時，等同全部顯示。
- 不顯示 `全部` 按鈕。

### Center Top: 關係地圖

中央上方維持 D3 force graph，作為主視覺。地圖只呈現目前人物與周邊關係，不承擔長文字閱讀。

### Center Bottom: 關係人物閱讀區

中央下方改為 `關係人物`，取代原本的人物資訊卡。它使用標籤切換，避免一次顯示太多分類：

- 全部
- 交戰
- 幫助
- 說服
- 受挫
- 主從
- 勝負轉折

每張關係人物卡顯示：

- 人物名
- 關係類型
- 第幾回
- 一句 GraphRAG 證據描述

點卡片後切換地圖焦點到該人物。

### Right: 人物檔案與時間軸

右側固定呈現較穩定的資料，適合上下捲動：

- 人物簡介：姓名、陣營、類型、簡介。
- 關鍵時刻：參與戰役、重要事件、加入陣營或轉折。
- 歷史本記：書中出現文字與章回脈絡。

右側不再放人物關係分類，避免與中央下方的關係人物區重複。

## Tech Stack

- Python generator creates a single-file HTML artifact.
- D3 v7 for graph.
- Vanilla JavaScript for UI state.
- No API, no Neo4j runtime, no external data fetch.

## Commands

Generate V15 local version:

```bash
python3 scripts/generate_sanguo_adventure_map_v15.py --output graphrag-demo/三國演義探險地圖_v15.html
```

Generate official local entry:

```bash
python3 scripts/generate_sanguo_adventure_map_v15.py --output 三國演義探險地圖.html
```

Generate GitHub Pages mirrors:

```bash
python3 scripts/generate_sanguo_adventure_map_v15.py --output graphrag-sanguo/page/三國演義探險地圖.html
python3 scripts/generate_sanguo_adventure_map_v15.py --output graphrag-sanguo/page/三國演義探險地圖_v15.html
```

Verify JavaScript:

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('graphrag-demo/三國演義探險地圖_v15.html','utf8'); const scripts=[...html.matchAll(/<script(?![^>]*application\\/json)[^>]*>([\\s\\S]*?)<\\/script>/g)].map(m=>m[1]); for (const s of scripts) new Function(s); console.log('scripts ok', scripts.length);"
```

## Project Structure

- `scripts/generate_sanguo_adventure_map_v15.py` -> V15 source generator.
- `docs/spec_sanguo_v15_person_explorer_layout.md` -> this spec.
- `graphrag-demo/三國演義探險地圖_v15.html` -> local versioned artifact.
- `三國演義探險地圖.html` -> local official artifact.
- `graphrag-sanguo/page/三國演義探險地圖.html` -> local GitHub Pages mirror.
- `graphrag-sanguo/page/三國演義探險地圖_v15.html` -> local versioned GitHub Pages mirror.

## Boundaries

- Always: keep the page shareable as one HTML file.
- Always: use the generator as the source of truth.
- Always: keep `人物探險`、`戰役推理`、`關係路徑` mode-specific.
- Never: show `全部` in the person-mode camp filter.
- Never: move relationship reading back into the narrow right panel.
- Never: require API, Neo4j, or external runtime.

## Success Criteria

- `人物探險` 左側 only contains start heroes, camp filter, search, and hero list.
- Camp filter has exactly four buttons: 魏、蜀、吳、其他.
- Camp filter supports select/cancel; no selection means all.
- `關係人物` appears in the center bottom with tab-like relation filters.
- Right panel shows人物檔案、關鍵時刻、歷史本記.
- Generated data remains `1534 nodes` and `6615 relationships`.
- HTML data version is `v15-person-explorer-layout`.
