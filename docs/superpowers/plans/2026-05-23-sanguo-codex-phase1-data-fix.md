# Phase 1 Data Fix — Strategy E: 從 extract/ 重跑合併

> **For agentic workers:** Use codex 作 implementer subagent，每 task 完成後 controller 補 commit 並 review。

**Goal:** 用 codex 重寫合併程式，把 `03_graphrag/extract/c001-c060_graph.json` 的 raw 抽取結果合併成新的 `nodes.json` / `rels.json`，徹底解決 v3 csv 與 unified jsonl 各自的合併 bug（諸葛亮、司馬懿、于禁、劉備、孫權等核心人物缺失）。

**Architecture:** raw extract 每章一份 json (entity local id) → 用 name + alias 跨章合併 → 重新 unified id → 計算 chapters/degree/isTrunk/camp → 推 category → 輸出新 nodes.json / rels.json，取代 build_graph.py 的 v3 csv 流。

**Tech Stack:** Python 3 標準庫，pytest 仍走 unittest。

---

## Spec 對映

- 主 spec `2026-05-23-sanguo-character-codex-design.md` § 6（GraphRAG 出題引擎所需 schema）
- 既有 Phase 1 plan 之 Task 2/3 的 build_graph.py / precompute_questions.py 結構與 schema
- 本 plan 補 Phase 1 plan 漏算的「raw extract 才是 ground truth、v3 csv 與 unified jsonl 都是 lossy 中間產物」這個事實

## 驗證標準（Data fix 完成意味著）

1. 新 `03_graphrag/nodes.json` 含以下核心人物（character entity）：
   - 諸葛亮、司馬懿、于禁、劉備、孫權、曹操、關羽、張飛、趙雲、周瑜
   - 每位 chapters ≥ 5、degree ≥ 5、isTrunk=True
2. 新 `03_graphrag/rels.json` 含 category 欄位（9 類：command/military/strategy/kinship/office/place/object/story/other），每條 relation 都有對應 category
3. 重跑 `precompute_questions.py` 後 character_personality.json 涵蓋諸葛亮（含 traits）
4. 既有 `05_pipeline/tests/test_build_graph.py` 與 `test_precompute_questions.py` 仍 pass（schema 兼容）
5. 新增 `test_merge_extracts.py` 至少 6 個 test 含核心人物驗證
6. `git status` 乾淨

---

## File Structure

**新增：**
- `05_pipeline/merge_extracts.py` — 主合併邏輯
- `05_pipeline/tests/test_merge_extracts.py` — 至少 6 個 test

**修改（重新產出，commit 進 git）：**
- `03_graphrag/nodes.json` — 從新合併程式輸出（取代 build_graph.py 輸出）
- `03_graphrag/rels.json` — 同上
- `03_graphrag/character_personality.json` — 重跑 precompute 後

**保留不動：**
- `05_pipeline/build_graph.py` 與其 tests — 仍服務 v3 csv 路徑（給想用 v3 的人；新 merge_extracts.py 是 primary path）
- `05_pipeline/precompute_questions.py` — 邏輯不變，只是吃新資料
- `03_graphrag/sanguo_v3_*.csv` — 保留作為 camp 對映參考來源
- `03_graphrag/unified/` — 保留作備援
- `03_graphrag/extract/c0XX_graph.json` — 不動

---

## Task A: 寫 merge_extracts.py 與 tests（最大塊）

**Files:**
- Create: `05_pipeline/merge_extracts.py`
- Create: `05_pipeline/tests/test_merge_extracts.py`

### 輸入 schema（每章 c0XX_graph.json）

```json
{
  "book": "三國演義",
  "chapter_no": 37,
  "chapter_title": "...",
  "model": "...",
  "entities": [
    {
      "id": "char_zhuge_liang",
      "name": "諸葛亮",
      "type": "character",
      "aliases": ["孔明", "臥龍"],
      "description": "..."
    }
  ],
  "relationships": [
    {
      "source": "char_zhuge_liang",
      "target": "char_liu_bei",
      "type": "事奉",
      "description": "...",
      "evidence": [...],
      "confidence": 1.0
    }
  ],
  "events": [...],
  "notes": "..."
}
```

### 輸出 schema（與 Phase 1 Task 2 的 build_graph.py 兼容）

每筆 node：
```json
{
  "id": "entity:character_諸葛亮",         // 統一格式：entity:<type>_<name>
  "name": "諸葛亮",
  "type": "character",
  "typeLabel": "人物",                     // 對映表
  "kind": "entity",                        // 一律 "entity"
  "camp": "shu",
  "campLabel": "劉蜀",
  "chapters": [36, 37, 38, ...],
  "chapterStart": 36,
  "chapterEnd": 60,
  "chapterCount": 22,
  "degree": 145,
  "score": 2900.0,
  "isTrunk": true,
  "aliases": ["孔明", "臥龍", "伏龍", ...],
  "description": "瑯琊陽都人..."              // 多章 description 合併（用「；」分隔）
}
```

每筆 relationship：
```json
{
  "id": "rel:000001",
  "source": "entity:character_諸葛亮",
  "target": "entity:character_劉備",
  "relationType": "事奉",                  // 原 type
  "category": "command",                    // 推導
  "categoryLabel": "陣營統率",
  "chapters": [37, 38, ...],
  "chapterStart": 37,
  "chapterEnd": 60,
  "weight": 5.0,                            // 同 source-target 出現次數
  "confidence": 1.0,
  "description": "徐庶推薦；隆中對策；...",
  "kind": "entity_relation"
}
```

### 合併規則

**Entity merge（跨章同人物識別）：**
1. 跨章 entity 若 name 完全相同 → 合併
2. 不同 name 但 aliases 有交集 → 合併（例：c045 出現 name="孔明" aliases=["諸葛亮"]）
3. 合併後：
   - 取 degree 最高的 description 為主，其他 append 用「；」分隔
   - aliases 取聯集
   - chapters 取聯集（int array）
   - type 取出現最多次的（投票）

**Relationship merge（同 source-target 同 type 跨章去重）：**
1. 把 local id 映射成 unified id（source 與 target 都要查 entity map）
2. (unified_source, unified_target, type) 三元組相同 → 合併
3. 合併後：chapters 聯集、weight = 出現次數、description append

**Camp 對映**（用既有 v3 csv 為 source of truth）：
1. 讀 `03_graphrag/sanguo_v3_nodes.csv` 抽取 name → (camp, campLabel) 表
2. 對新合併 entity，若 name 在表 → 套用；不在 → camp="other", campLabel="其他"
3. 對於 v3 csv 缺失但本次新合併出來的核心人物（諸葛亮等），在 merge_extracts.py 內 hard-code 一個 fallback dict，例：
   ```python
   CAMP_FALLBACK = {
     "諸葛亮": ("shu", "劉蜀"),
     "司馬懿": ("wei", "曹魏"),
     "于禁": ("wei", "曹魏"),
     ...
   }
   ```
   覆蓋順序：CAMP_FALLBACK > v3 csv > "other"

**Category 推導（relationship.type → category）：**
從既有 v3 rels 學 mapping：
1. 讀 v3 rels csv，建 (source_name, target_name, type) → category lookup
2. 對新 rel：先查 lookup
3. 沒對到 → 套字串規則：
   - 含「結/拜/兄/弟/父/母/子/女/夫/妻/族」→ kinship
   - 含「攻/戰/敗/破/殺/俘」→ military
   - 含「事/從/拜/降/封」→ command
   - 含「計/策/騙/智/謀」→ strategy
   - 含「治/守/在/住」→ place
   - 含「任/官/職/拜/封/賜」→ office
   - 其他 → story

**Score 計算：** `score = degree * len(chapters)`（與 v3 csv 邏輯一致）

**isTrunk 判定：** `degree >= 10 OR len(chapters) >= 10`

### CLI

```bash
python3 05_pipeline/merge_extracts.py
# 預設讀 03_graphrag/extract/c001-c060_graph.json + 03_graphrag/sanguo_v3_nodes.csv
# 預設輸出 03_graphrag/nodes.json + rels.json（覆寫 build_graph.py 的輸出）
```

### Tests (test_merge_extracts.py)

1. **諸葛亮存在於 nodes.json** 且 chapters ≥ 5, degree ≥ 5, isTrunk=True, camp="shu"
2. **司馬懿存在於 nodes.json** 且 chapterCount > 1, camp="wei"
3. **于禁存在於 nodes.json** camp="wei"
4. **劉備依然存在** chapters ≥ 50, degree ≥ 100
5. **每條 relationship 都有 category 且屬於 9 類**
6. **同人物跨章 local id 已合併**：例如 char_zhuge_liang 與 c038_char_zhuge_liang 在 rels.json 中對應同一個 unified id

---

## Task B: 重跑 precompute_questions + 兼容測試

- [ ] **B-1: 跑 merge_extracts.py 產出新 nodes.json/rels.json**

```bash
python3 05_pipeline/merge_extracts.py
```

- [ ] **B-2: 重跑 precompute_questions.py**

```bash
python3 05_pipeline/precompute_questions.py
```

- [ ] **B-3: 驗證諸葛亮有個性檔**

```bash
python3 -c "
import json
d = json.load(open('03_graphrag/character_personality.json', encoding='utf-8'))
zhu = next((v for v in d.values() if v['name']=='諸葛亮'), None)
print('諸葛亮:', zhu)
"
```
Expected：traits 非空、ratios 含 strategy / command。

- [ ] **B-4: 跑既有 test_build_graph 確認新 nodes.json 仍符合 schema**

```bash
python3 -m unittest 05_pipeline.tests.test_build_graph -v
```
Expected：8 tests pass（新資料對 schema 兼容）。

- [ ] **B-5: 跑 test_merge_extracts**

```bash
python3 -m unittest 05_pipeline.tests.test_merge_extracts -v
```
Expected：6+ tests pass。

- [ ] **B-6: 跑全部 pipeline 測試**

```bash
python3 -m unittest discover -s 05_pipeline/tests -v
```
Expected：21+ tests pass。

---

## Task C: Commit 與 known issues 更新

由 controller 補做：
1. commit 新 merge_extracts.py + tests + 新 nodes.json/rels.json/character_personality.json
2. 更新主 spec `2026-05-23-sanguo-character-codex-design.md` § 6 註明 personality denominator 與 category 推導規則
3. 更新 README.md「資料規模」與「03_graphrag 內容」反映新數字

---

## Phase 1 Data Fix 完成檢查清單

- [ ] `05_pipeline/merge_extracts.py` 存在
- [ ] `05_pipeline/tests/test_merge_extracts.py` 含 6+ tests 全 pass
- [ ] 新 `03_graphrag/nodes.json` 含 character 諸葛亮（chapters ≥ 5, degree ≥ 5）
- [ ] 同含 司馬懿、于禁、劉備、孫權
- [ ] 新 `03_graphrag/rels.json` 每條都有 category（9 類之一）
- [ ] 新 `03_graphrag/character_personality.json` 含諸葛亮 entry
- [ ] 既有 `test_build_graph` 與 `test_precompute_questions` 仍 pass
- [ ] git history 乾淨、commit message 反映完整改動
