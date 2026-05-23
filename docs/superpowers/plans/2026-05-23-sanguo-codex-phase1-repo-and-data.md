# Sanguo Character Codex — Phase 1: Repo 整併與資料外掛 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `台科課程實作/` 內的 GraphRAG 原始資料搬進 `GraphRag-Game/`，把資料從 hardcoded HTML 拆成可被前端 fetch 的 JSON 檔，並歸檔舊版 HTML——為後續 Phase 2 的引擎與 UI 鋪好資料層基礎。

**Architecture:** 在 `GraphRag-Game/` 內新增 `05_pipeline/` 放 Python 轉檔腳本（csv → json + 預算個性比例），輸出 `03_graphrag/*.json`；舊版 HTML 移到 `04_app/_archive/`；根目錄主 HTML 改成 meta-refresh 轉址檔，保留舊 URL 相容。本 phase 只動資料與 pipeline，不動前端應用本體。

**Tech Stack:** Python 3 標準庫（csv / json / pathlib / unittest），無外部依賴；shell `git mv` 搬檔。

**Spec 對映:**
- 主 spec `2026-05-23-sanguo-character-codex-design.md` § 8（部署架構） + § 9（從現況遷移）
- 介面 spec 本 phase 不涉及

**驗證標準（Phase 1 完成意味著）:**
1. `03_graphrag/` 下有 `sanguo_v3_nodes.csv`、`sanguo_v3_relationships.csv`、`metadata.json`、`nodes.json`、`rels.json`、`character_personality.json`
2. `05_pipeline/` 下有 `build_graph.py`、`precompute_questions.py`、`tests/` 且 `python3 -m unittest discover -s 05_pipeline/tests` 全 pass
3. `04_app/_archive/` 內含 v15/v16/v17 HTML 與 .htm
4. 根目錄 `三國演義探險地圖.html` 改為轉址檔，瀏覽器點下會跳到 `04_app/三國演義探險地圖_v17.html`（Phase 2 後改指 `04_app/index.html`）
5. `README.md` 反映新目錄結構與三層架構（source → pipeline → app）
6. 所有改動分階段 commit，不在單一 commit 內混雜搬檔 + 邏輯

---

## File Structure

**新增（本 phase 產出）：**
- `03_graphrag/sanguo_v3_nodes.csv`（從台科搬）
- `03_graphrag/sanguo_v3_relationships.csv`（從台科搬）
- `03_graphrag/metadata.json`（從台科搬）
- `03_graphrag/nodes.json`（build_graph.py 產出）
- `03_graphrag/rels.json`（build_graph.py 產出）
- `03_graphrag/character_personality.json`（precompute_questions.py 產出）
- `05_pipeline/build_graph.py`（csv → json 轉換）
- `05_pipeline/precompute_questions.py`（統計人物個性比例）
- `05_pipeline/tests/__init__.py`（空檔讓 unittest discover）
- `05_pipeline/tests/test_build_graph.py`
- `05_pipeline/tests/test_precompute_questions.py`
- `05_pipeline/README.md`（pipeline 使用說明）
- `04_app/_archive/`（目錄，內含舊 HTML）

**修改：**
- `三國演義探險地圖.html`（根目錄）→ 改為 meta-refresh 轉址檔
- `README.md` → 三層架構說明

**搬移（git mv，不重寫）：**
- `04_app/三國演義探險地圖_v15.html` → `04_app/_archive/`
- `04_app/三國演義探險地圖_v16.html` → `04_app/_archive/`
- `04_app/三國演義探險地圖_v17.html` → 保留在 `04_app/`（Phase 1 末仍是 fallback 主檔）
- `04_app/三國演義探險地圖.htm` → `04_app/_archive/`（重複檔）

**不動的:**
- `01_source/`、`02_chapters/`、既有的 `03_graphrag/embeddings|extract|prompts|unified|settings.yaml`、`04_app/三國演義探險地圖_v17.html`、`docs/`、`index.html`

---

## Task 1: 建立 Phase 1 目錄結構並搬移原始 GraphRAG v3 資料

**Files:**
- Create dir: `03_graphrag/` （已存在，但要搬新檔進去）
- Create dir: `04_app/_archive/`
- Create dir: `05_pipeline/`
- Create dir: `05_pipeline/tests/`
- Copy: `/Users/s389080/Documents/doc/work/0_AI_Project/testProject/台科課程實作/graphrag-sanguo/sanguo_neo4j_v3/import/sanguo_v3_nodes.csv` → `03_graphrag/sanguo_v3_nodes.csv`
- Copy: `.../sanguo_v3_relationships.csv` → `03_graphrag/sanguo_v3_relationships.csv`
- Copy: `.../graphrag-sanguo/sanguo_neo4j_v3/metadata.json` → `03_graphrag/metadata.json`

- [ ] **Step 1: 建立新目錄**

```bash
mkdir -p 04_app/_archive 05_pipeline/tests
```

驗證：
```bash
ls -la 04_app/_archive 05_pipeline/tests
```
Expected：兩個空目錄存在（macOS 可能含 `.DS_Store`）

- [ ] **Step 2: 從台科課程實作 copy v3 GraphRAG 資料**

```bash
cp "/Users/s389080/Documents/doc/work/0_AI_Project/testProject/台科課程實作/graphrag-sanguo/sanguo_neo4j_v3/import/sanguo_v3_nodes.csv" 03_graphrag/sanguo_v3_nodes.csv
cp "/Users/s389080/Documents/doc/work/0_AI_Project/testProject/台科課程實作/graphrag-sanguo/sanguo_neo4j_v3/import/sanguo_v3_relationships.csv" 03_graphrag/sanguo_v3_relationships.csv
cp "/Users/s389080/Documents/doc/work/0_AI_Project/testProject/台科課程實作/graphrag-sanguo/sanguo_neo4j_v3/metadata.json" 03_graphrag/metadata.json
```

註：用 `cp` 不是 `mv`，因為台科原檔可能還會被開發者參考。

- [ ] **Step 3: 驗證檔案在位**

```bash
ls -la 03_graphrag/sanguo_v3_nodes.csv 03_graphrag/sanguo_v3_relationships.csv 03_graphrag/metadata.json
wc -l 03_graphrag/sanguo_v3_nodes.csv 03_graphrag/sanguo_v3_relationships.csv
```
Expected：
- `sanguo_v3_nodes.csv` ≈ 1535 行
- `sanguo_v3_relationships.csv` ≈ 6616 行
- `metadata.json` 存在約 413 行

- [ ] **Step 4: Commit**

```bash
git add 03_graphrag/sanguo_v3_nodes.csv 03_graphrag/sanguo_v3_relationships.csv 03_graphrag/metadata.json 04_app/_archive 05_pipeline/tests
git commit -m "chore: import sanguo v3 graphrag data and scaffold pipeline dirs

把台科課程實作端的 sanguo_v3_nodes.csv / relationships.csv /
metadata.json 搬進 GraphRag-Game/03_graphrag/，並建立
04_app/_archive 與 05_pipeline/tests 目錄為 Phase 1 後續任務鋪路。"
```

註：macOS 上空目錄不會被 git 追蹤。若 `04_app/_archive` 與 `05_pipeline/tests` 為空，commit 不會包含——這 OK，後續 task 會放檔案進去。可以暫先在每目錄 touch 一個 `.gitkeep`：
```bash
touch 04_app/_archive/.gitkeep 05_pipeline/tests/.gitkeep
git add 04_app/_archive/.gitkeep 05_pipeline/tests/.gitkeep
git commit --amend --no-edit
```

---

## Task 2: build_graph.py — 把 csv 轉成前端可 fetch 的 JSON

**Files:**
- Create: `05_pipeline/build_graph.py`
- Create: `05_pipeline/tests/test_build_graph.py`
- Test command: `python3 -m unittest 05_pipeline.tests.test_build_graph -v`

**設計目標：**
- 讀 `03_graphrag/sanguo_v3_nodes.csv` → 產 `03_graphrag/nodes.json`
- 讀 `03_graphrag/sanguo_v3_relationships.csv` → 產 `03_graphrag/rels.json`
- 把 csv 內 `;` 分隔字串（chapters / aliases）轉成 array
- 把 `weight` / `confidence` / `degree` 等數字欄位轉成數值型
- 過濾不必要 columns（如 `kind` 在 nodes csv 與 entity 同義，保留即可）
- JSON 為 prettified UTF-8（方便 git diff），但用 `ensure_ascii=False` 保留中文

- [ ] **Step 1: 寫第一個失敗測試 — 確認 build_graph 把 csv 行數對應到 json node 數**

Create `05_pipeline/tests/__init__.py`（空檔，讓 unittest 認識為 package）：

```bash
: > 05_pipeline/tests/__init__.py
: > 05_pipeline/__init__.py
```

Create `05_pipeline/tests/test_build_graph.py`：

```python
"""Tests for build_graph: csv → json 轉換 pipeline."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "05_pipeline"))

import build_graph  # noqa: E402


class BuildGraphSmokeTest(unittest.TestCase):
    """跑真實 csv 一遍，確認 json 結構正確。"""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="build_graph_test_"))
        cls.nodes_csv = REPO_ROOT / "03_graphrag" / "sanguo_v3_nodes.csv"
        cls.rels_csv = REPO_ROOT / "03_graphrag" / "sanguo_v3_relationships.csv"
        cls.nodes_json = cls.tmpdir / "nodes.json"
        cls.rels_json = cls.tmpdir / "rels.json"
        build_graph.build(
            nodes_csv=cls.nodes_csv,
            rels_csv=cls.rels_csv,
            nodes_out=cls.nodes_json,
            rels_out=cls.rels_json,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_nodes_json_row_count_matches_csv(self):
        # csv 有 header + 1534 data rows
        with open(self.nodes_csv, encoding="utf-8") as f:
            csv_rows = sum(1 for _ in f) - 1
        with open(self.nodes_json, encoding="utf-8") as f:
            nodes = json.load(f)
        self.assertEqual(len(nodes), csv_rows)

    def test_rels_json_row_count_matches_csv(self):
        with open(self.rels_csv, encoding="utf-8") as f:
            csv_rows = sum(1 for _ in f) - 1
        with open(self.rels_json, encoding="utf-8") as f:
            rels = json.load(f)
        self.assertEqual(len(rels), csv_rows)

    def test_chapters_field_is_int_array(self):
        with open(self.nodes_json, encoding="utf-8") as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n["name"] == "曹操")
        self.assertIsInstance(cao_cao["chapters"], list)
        for ch in cao_cao["chapters"]:
            self.assertIsInstance(ch, int)
        # 曹操在 60 章中應該至少出現 50 章
        self.assertGreater(len(cao_cao["chapters"]), 50)

    def test_aliases_field_is_string_array(self):
        with open(self.nodes_json, encoding="utf-8") as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n["name"] == "曹操")
        self.assertIsInstance(cao_cao["aliases"], list)
        self.assertIn("孟德", cao_cao["aliases"])

    def test_isTrunk_is_bool(self):
        with open(self.nodes_json, encoding="utf-8") as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n["name"] == "曹操")
        self.assertIsInstance(cao_cao["isTrunk"], bool)
        self.assertTrue(cao_cao["isTrunk"])

    def test_numeric_fields_are_numbers(self):
        with open(self.nodes_json, encoding="utf-8") as f:
            nodes = json.load(f)
        cao_cao = next(n for n in nodes if n["name"] == "曹操")
        self.assertIsInstance(cao_cao["degree"], int)
        self.assertIsInstance(cao_cao["score"], (int, float))

    def test_rel_chapters_is_int_array(self):
        with open(self.rels_json, encoding="utf-8") as f:
            rels = json.load(f)
        sample = rels[0]
        self.assertIsInstance(sample["chapters"], list)
        if sample["chapters"]:
            self.assertIsInstance(sample["chapters"][0], int)

    def test_rel_weight_confidence_are_numeric(self):
        with open(self.rels_json, encoding="utf-8") as f:
            rels = json.load(f)
        sample = rels[0]
        self.assertIsInstance(sample["weight"], (int, float))
        self.assertIsInstance(sample["confidence"], float)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試確認失敗（檔案不存在）**

```bash
python3 -m unittest 05_pipeline.tests.test_build_graph -v
```
Expected：`ModuleNotFoundError: No module named 'build_graph'`

- [ ] **Step 3: 寫 build_graph.py 最小實作**

Create `05_pipeline/build_graph.py`：

```python
#!/usr/bin/env python3
"""Convert sanguo v3 csv (nodes & relationships) into prettified JSON.

讀 03_graphrag/ 下的 csv，轉成前端可直接 fetch 的 nodes.json / rels.json。
不引外部依賴，只用 Python 標準庫。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES_CSV = REPO_ROOT / "03_graphrag" / "sanguo_v3_nodes.csv"
DEFAULT_RELS_CSV = REPO_ROOT / "03_graphrag" / "sanguo_v3_relationships.csv"
DEFAULT_NODES_OUT = REPO_ROOT / "03_graphrag" / "nodes.json"
DEFAULT_RELS_OUT = REPO_ROOT / "03_graphrag" / "rels.json"


def _split_int_list(raw: str) -> list[int]:
    """`'1;2;3'` → `[1, 2, 3]`；空字串或 None → `[]`。"""
    if not raw:
        return []
    return [int(x) for x in raw.split(";") if x.strip()]


def _split_str_list(raw: str) -> list[str]:
    """`'孟德|阿瞞'` → `['孟德', '阿瞞']`；空 → `[]`。"""
    if not raw:
        return []
    return [x.strip() for x in raw.split("|") if x.strip()]


def _to_bool(raw: str) -> bool:
    return raw.strip().lower() == "true"


def _to_int(raw: str, default: int = 0) -> int:
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def _to_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (ValueError, TypeError):
        return default


def _convert_node(row: dict[str, str]) -> dict[str, Any]:
    """Node csv row → typed dict.

    csv schema:
      id, name, type, typeLabel, kind, camp, campLabel,
      chapters, chapterStart, chapterEnd, chapterCount,
      degree, score, isTrunk, aliases, description
    """
    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "typeLabel": row["typeLabel"],
        "kind": row["kind"],
        "camp": row["camp"],
        "campLabel": row["campLabel"],
        "chapters": _split_int_list(row.get("chapters", "")),
        "chapterStart": _to_int(row.get("chapterStart")),
        "chapterEnd": _to_int(row.get("chapterEnd")),
        "chapterCount": _to_int(row.get("chapterCount")),
        "degree": _to_int(row.get("degree")),
        "score": _to_float(row.get("score")),
        "isTrunk": _to_bool(row.get("isTrunk", "")),
        "aliases": _split_str_list(row.get("aliases", "")),
        "description": row.get("description", ""),
    }


def _convert_rel(row: dict[str, str]) -> dict[str, Any]:
    """Relationship csv row → typed dict.

    csv schema:
      id, source, target, relationType, category, categoryLabel,
      chapters, chapterStart, chapterEnd, weight, confidence,
      description, kind
    """
    return {
        "id": row["id"],
        "source": row["source"],
        "target": row["target"],
        "relationType": row["relationType"],
        "category": row["category"],
        "categoryLabel": row["categoryLabel"],
        "chapters": _split_int_list(row.get("chapters", "")),
        "chapterStart": _to_int(row.get("chapterStart")),
        "chapterEnd": _to_int(row.get("chapterEnd")),
        "weight": _to_float(row.get("weight")),
        "confidence": _to_float(row.get("confidence")),
        "description": row.get("description", ""),
        "kind": row.get("kind", ""),
    }


def build(
    nodes_csv: Path = DEFAULT_NODES_CSV,
    rels_csv: Path = DEFAULT_RELS_CSV,
    nodes_out: Path = DEFAULT_NODES_OUT,
    rels_out: Path = DEFAULT_RELS_OUT,
) -> None:
    with open(nodes_csv, encoding="utf-8", newline="") as f:
        nodes = [_convert_node(row) for row in csv.DictReader(f)]
    nodes_out.parent.mkdir(parents=True, exist_ok=True)
    with open(nodes_out, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(nodes)} nodes to {nodes_out}", file=sys.stderr)

    with open(rels_csv, encoding="utf-8", newline="") as f:
        rels = [_convert_rel(row) for row in csv.DictReader(f)]
    with open(rels_out, "w", encoding="utf-8") as f:
        json.dump(rels, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(rels)} relationships to {rels_out}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes-csv", type=Path, default=DEFAULT_NODES_CSV)
    parser.add_argument("--rels-csv", type=Path, default=DEFAULT_RELS_CSV)
    parser.add_argument("--nodes-out", type=Path, default=DEFAULT_NODES_OUT)
    parser.add_argument("--rels-out", type=Path, default=DEFAULT_RELS_OUT)
    args = parser.parse_args()
    build(args.nodes_csv, args.rels_csv, args.nodes_out, args.rels_out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑測試確認通過**

```bash
python3 -m unittest 05_pipeline.tests.test_build_graph -v
```
Expected：8 tests, all PASS。輸出含 `wrote 1534 nodes to ...` 與 `wrote 6615 relationships to ...`。

- [ ] **Step 5: 跑 CLI 一次產出實際檔**

```bash
python3 05_pipeline/build_graph.py
ls -la 03_graphrag/nodes.json 03_graphrag/rels.json
```
Expected：兩檔存在，nodes.json ~700 KB、rels.json ~2.5 MB。

- [ ] **Step 6: 抽樣驗證 JSON 結構**

```bash
python3 -c "
import json
nodes = json.load(open('03_graphrag/nodes.json', encoding='utf-8'))
cao = next(n for n in nodes if n['name'] == '曹操')
print('曹操 chapters first 5:', cao['chapters'][:5])
print('曹操 aliases first 3:', cao['aliases'][:3])
print('曹操 isTrunk:', cao['isTrunk'])
print('曹操 degree:', cao['degree'])
"
```
Expected：chapters 是 `[1, 2, 3, 4, 5]`、aliases 含 `司空曹操` 等、`isTrunk: True`、degree 為整數。

- [ ] **Step 7: Commit**

```bash
git add 05_pipeline/__init__.py 05_pipeline/build_graph.py 05_pipeline/tests/__init__.py 05_pipeline/tests/test_build_graph.py 03_graphrag/nodes.json 03_graphrag/rels.json
git commit -m "feat(pipeline): add build_graph.py csv→json converter with tests

讀 03_graphrag/ 下的 sanguo_v3_*.csv，把 ';' 分隔字串轉成
array、把數字欄位轉成數值型，產出 nodes.json (1534) 與
rels.json (6615) 給前端 fetch。含 8 個 unit test 覆蓋
欄位型別、行數一致、邊界 case。"
```

---

## Task 3: precompute_questions.py — 預算人物個性比例

**Files:**
- Create: `05_pipeline/precompute_questions.py`
- Create: `05_pipeline/tests/test_precompute_questions.py`
- Output: `03_graphrag/character_personality.json`
- Test command: `python3 -m unittest 05_pipeline.tests.test_precompute_questions -v`

**設計目標（對應主 spec § 6 個性配對題）：**
- 對每個 `kind=entity` 且 `type=character` 的人物，統計其所有 outgoing relationship 的 category 比例
- 套用閾值規則（主 spec § 6）：
  - `strategy > 20%` → `會算計`
  - `command > 25%` → `會帶人`
  - `military > 30%` → `會打仗`
  - `kinship > 10%` → `重感情`
- 輸出每人物：`{ id, name, ratios: {category: pct}, traits: ["會算計", "會帶人"] }`
- 只處理 isTrunk 人物（避免次要人物雜訊），但保留欄位讓前端可顯示非 trunk

- [ ] **Step 1: 寫失敗測試**

Create `05_pipeline/tests/test_precompute_questions.py`：

```python
"""Tests for precompute_questions: 個性比例與 traits 預算。"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "05_pipeline"))

import precompute_questions  # noqa: E402


class PrecomputeQuestionsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="precompute_test_"))
        cls.nodes_json = REPO_ROOT / "03_graphrag" / "nodes.json"
        cls.rels_json = REPO_ROOT / "03_graphrag" / "rels.json"
        cls.out_json = cls.tmpdir / "character_personality.json"
        precompute_questions.compute(
            nodes_json=cls.nodes_json,
            rels_json=cls.rels_json,
            output=cls.out_json,
        )
        with open(cls.out_json, encoding="utf-8") as f:
            cls.data = json.load(f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_output_is_dict_keyed_by_id(self):
        self.assertIsInstance(self.data, dict)
        self.assertIn("entity:character_曹操", self.data)

    def test_each_entry_has_required_fields(self):
        entry = self.data["entity:character_曹操"]
        self.assertIn("id", entry)
        self.assertIn("name", entry)
        self.assertIn("ratios", entry)
        self.assertIn("traits", entry)
        self.assertEqual(entry["name"], "曹操")

    def test_ratios_sum_to_approx_one(self):
        entry = self.data["entity:character_曹操"]
        total = sum(entry["ratios"].values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_cao_cao_has_command_or_strategy_trait(self):
        entry = self.data["entity:character_曹操"]
        # 曹操關係多為策略與統率，應至少觸發其中一個
        self.assertTrue(
            "會算計" in entry["traits"] or "會帶人" in entry["traits"],
            f"曹操 traits 應含 會算計 或 會帶人，實際: {entry['traits']}",
        )

    def test_traits_are_unique(self):
        for entry in self.data.values():
            self.assertEqual(len(entry["traits"]), len(set(entry["traits"])))

    def test_only_character_entities_present(self):
        # 不該有事件或地點
        for entry_id in self.data.keys():
            self.assertIn("character_", entry_id, f"非人物 id 混入: {entry_id}")

    def test_ratios_categories_known_set(self):
        known = {"command", "military", "strategy", "kinship", "office",
                 "place", "story", "object", "other"}
        for entry in self.data.values():
            for cat in entry["ratios"].keys():
                self.assertIn(cat, known, f"未知 category: {cat}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
python3 -m unittest 05_pipeline.tests.test_precompute_questions -v
```
Expected：`ModuleNotFoundError: No module named 'precompute_questions'`

- [ ] **Step 3: 寫 precompute_questions.py**

Create `05_pipeline/precompute_questions.py`：

```python
#!/usr/bin/env python3
"""Compute per-character personality ratios and traits.

讀 nodes.json / rels.json，對每個 character entity 統計 outgoing
relationship 的 category 比例，套用閾值產出 traits。輸出
character_personality.json，給前端「個性配對」題型與圖鑑詳情頁使用。
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES_JSON = REPO_ROOT / "03_graphrag" / "nodes.json"
DEFAULT_RELS_JSON = REPO_ROOT / "03_graphrag" / "rels.json"
DEFAULT_OUTPUT = REPO_ROOT / "03_graphrag" / "character_personality.json"

# 主 spec § 6 個性配對閾值（plan 階段可調，此處依 spec 初版）
TRAIT_THRESHOLDS = [
    ("strategy", 0.20, "會算計"),
    ("command", 0.25, "會帶人"),
    ("military", 0.30, "會打仗"),
    ("kinship", 0.10, "重感情"),
]


def _is_character(node: dict[str, Any]) -> bool:
    return node.get("kind") == "entity" and node.get("type") == "character"


def _compute_ratios(rels: list[dict[str, Any]], subject_id: str) -> dict[str, float]:
    counter: Counter[str] = Counter()
    for rel in rels:
        if rel["source"] == subject_id:
            counter[rel.get("category", "other")] += 1
    total = sum(counter.values())
    if total == 0:
        return {}
    return {cat: round(count / total, 4) for cat, count in counter.items()}


def _derive_traits(ratios: dict[str, float]) -> list[str]:
    traits: list[str] = []
    for category, threshold, label in TRAIT_THRESHOLDS:
        if ratios.get(category, 0.0) >= threshold:
            traits.append(label)
    return traits


def compute(
    nodes_json: Path = DEFAULT_NODES_JSON,
    rels_json: Path = DEFAULT_RELS_JSON,
    output: Path = DEFAULT_OUTPUT,
) -> None:
    with open(nodes_json, encoding="utf-8") as f:
        nodes = json.load(f)
    with open(rels_json, encoding="utf-8") as f:
        rels = json.load(f)

    result: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not _is_character(node):
            continue
        ratios = _compute_ratios(rels, node["id"])
        if not ratios:
            continue
        result[node["id"]] = {
            "id": node["id"],
            "name": node["name"],
            "ratios": ratios,
            "traits": _derive_traits(ratios),
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(result)} character personalities to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes-json", type=Path, default=DEFAULT_NODES_JSON)
    parser.add_argument("--rels-json", type=Path, default=DEFAULT_RELS_JSON)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    compute(args.nodes_json, args.rels_json, args.output)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑測試確認通過**

```bash
python3 -m unittest 05_pipeline.tests.test_precompute_questions -v
```
Expected：7 tests, all PASS。

- [ ] **Step 5: 跑 CLI 產出實檔**

```bash
python3 05_pipeline/precompute_questions.py
ls -la 03_graphrag/character_personality.json
```

- [ ] **Step 6: 抽樣驗證**

```bash
python3 -c "
import json
data = json.load(open('03_graphrag/character_personality.json', encoding='utf-8'))
for name in ['曹操', '劉備', '諸葛亮', '張飛', '呂布']:
    entry = next((e for e in data.values() if e['name'] == name), None)
    if entry:
        top3 = sorted(entry['ratios'].items(), key=lambda x: -x[1])[:3]
        print(f\"{name}: traits={entry['traits']}, top3={top3}\")
"
```
Expected：每人輸出 1-3 個 traits 與前 3 大 category 比例。例如曹操可能是 `traits=['會算計', '會帶人']`。

- [ ] **Step 7: 跑全部 pipeline 測試**

```bash
python3 -m unittest discover -s 05_pipeline/tests -v
```
Expected：15 tests (8 build_graph + 7 precompute), all PASS。

- [ ] **Step 8: Commit**

```bash
git add 05_pipeline/precompute_questions.py 05_pipeline/tests/test_precompute_questions.py 03_graphrag/character_personality.json
git commit -m "feat(pipeline): add precompute_questions.py for personality ratios

對每個 character entity 統計 outgoing relationship 的 category
比例，套用主 spec § 6 閾值（strategy/command/military/kinship）
產出 traits 標籤。輸出 character_personality.json 給前端
個性配對題與圖鑑詳情用。含 7 個 unit test 覆蓋欄位、總和、
類別白名單。"
```

---

## Task 4: 把舊版 v15 / v16 / htm 歸檔到 `04_app/_archive/`

**Files:**
- Move: `04_app/三國演義探險地圖_v15.html` → `04_app/_archive/三國演義探險地圖_v15.html`
- Move: `04_app/三國演義探險地圖_v16.html` → `04_app/_archive/三國演義探險地圖_v16.html`
- Move: `04_app/三國演義探險地圖.htm` → `04_app/_archive/三國演義探險地圖.htm`
- 保留：`04_app/三國演義探險地圖_v17.html` 與 `04_app/三國演義探險地圖.html`（後者是 v17 副本，Phase 1 仍作 fallback）

- [ ] **Step 1: 用 git mv 移動舊版檔**

```bash
git mv "04_app/三國演義探險地圖_v15.html" "04_app/_archive/三國演義探險地圖_v15.html"
git mv "04_app/三國演義探險地圖_v16.html" "04_app/_archive/三國演義探險地圖_v16.html"
git mv "04_app/三國演義探險地圖.htm" "04_app/_archive/三國演義探險地圖.htm"
```

註：`git mv` 比 `mv + git add/rm` 好，可保留 git history 連續性。

- [ ] **Step 2: 驗證移動成功**

```bash
ls 04_app/
ls 04_app/_archive/
```
Expected：
- `04_app/` 只剩 `三國演義探險地圖.html`、`三國演義探險地圖_v17.html`
- `04_app/_archive/` 內含 `_v15.html`、`_v16.html`、`.htm`、`.gitkeep`

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: archive sanguo v15/v16/htm into 04_app/_archive

保留 v17 為當前 fallback 主檔（Phase 2 會替換為新 index.html），
v15/v16/htm 移到 _archive 不擋路但保留歷史。"
```

---

## Task 5: 根目錄 `三國演義探險地圖.html` 改為 meta-refresh 轉址檔

**Files:**
- Replace: `三國演義探險地圖.html`（根目錄）— 從 3.9 MB v17 副本改為 < 1 KB 轉址檔

**設計目標：**
- 任何外部連到舊 URL（GitHub Pages 的 `/三國演義探險地圖.html`）的都會自動跳到 `04_app/三國演義探險地圖_v17.html`
- Phase 2 完成後，這支轉址檔的 target 會改成 `04_app/index.html`，但 Phase 1 暫指 v17
- 加 `<noscript>` fallback 與 `<a>` 連結，無 JS / meta-refresh 也能手動點進

- [ ] **Step 1: 備份原檔到 _archive**

```bash
git mv "三國演義探險地圖.html" "04_app/_archive/三國演義探險地圖_root_backup.html"
```
（這支根目錄的本來就是 v17 的副本，archive 起來不會浪費；後續會在原位置寫新轉址檔）

- [ ] **Step 2: 寫新轉址檔**

Create `三國演義探險地圖.html`（根目錄）：

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<title>三國演義探險地圖</title>
<meta http-equiv="refresh" content="0; url=04_app/三國演義探險地圖_v17.html">
<link rel="canonical" href="04_app/三國演義探險地圖_v17.html">
<style>
  body { font-family: -apple-system, "Noto Sans TC", sans-serif;
         display: flex; min-height: 100vh; align-items: center;
         justify-content: center; margin: 0; background: #FFF7ED;
         color: #1E293B; }
  .card { padding: 32px 24px; max-width: 480px; text-align: center;
          line-height: 1.7; }
  a { color: #F97316; font-weight: 600; }
</style>
</head>
<body>
<main class="card">
  <h1>三國演義探險地圖</h1>
  <p>正在帶你前往最新版本…</p>
  <p><noscript>如果沒有自動跳轉，請</noscript>
     <a href="04_app/三國演義探險地圖_v17.html">點此手動進入</a>。</p>
</main>
<script>
  // 雙重保險：若 meta refresh 被瀏覽器擋掉，用 JS 跳轉
  setTimeout(() => { location.replace('04_app/三國演義探險地圖_v17.html'); }, 50);
</script>
</body>
</html>
```

- [ ] **Step 3: 驗證檔案大小與內容**

```bash
ls -la 三國演義探險地圖.html
wc -l 三國演義探險地圖.html
head -3 三國演義探險地圖.html
```
Expected：檔案 < 2 KB（不是 3.9 MB），首行為 `<!doctype html>`。

- [ ] **Step 4: 手動瀏覽器驗證（必跑）**

```bash
echo "請在瀏覽器打開 file://$(pwd)/三國演義探險地圖.html 確認會自動跳轉到 v17 介面（會看到 v17 的探險地圖 UI）"
open "三國演義探險地圖.html"
```
Expected：瀏覽器 < 1 秒自動跳到 v17 介面。手動驗證後回到 terminal 繼續。

- [ ] **Step 5: Commit**

```bash
git add 三國演義探險地圖.html
git commit -m "feat: replace root 三國演義探險地圖.html with meta-refresh redirect

把 3.9 MB v17 副本替換為 < 2 KB 轉址檔，跳到
04_app/三國演義探險地圖_v17.html。保留舊 URL 相容性，
未來 Phase 2 完成後只需改 target 為 04_app/index.html。
含 noscript fallback + JS 雙保險。"
```

---

## Task 6: 更新 `README.md` 反映 Phase 1 後的目錄結構

**Files:**
- Modify: `README.md`

**設計目標：**
- 把 README 改成「source → pipeline → app」三層架構說明
- 加 build 步驟（pipeline 怎麼跑）
- 加 archive 說明
- 不刪原有專案脈絡，但更新已過時的描述

- [ ] **Step 1: 讀現有 README 找要改的段落**

```bash
cat README.md
```

- [ ] **Step 2: 改寫 README（保留 frontmatter / 標題，重寫主體）**

Create `README.md`（完整覆蓋）：

```markdown
# 三國演義探險地圖（GraphRag-Game）

把 GraphRAG 抽取的《三國演義》知識圖譜做成兒童自學的人物識讀網站。
透過「人物圖鑑 × 關係偵探」的遊戲循環，孩子能從關係推理中認識 60 位主要人物。

## 三層架構

```
01_source/      小說原文（zip）
02_chapters/    章節 markdown（c001.md ~ c060.md）
03_graphrag/    GraphRAG 圖譜資料
                ├── sanguo_v3_nodes.csv          原始 CSV
                ├── sanguo_v3_relationships.csv
                ├── metadata.json
                ├── nodes.json                   ← pipeline 產出，前端 fetch
                ├── rels.json
                └── character_personality.json
04_app/         前端
                ├── 三國演義探險地圖_v17.html    當前 fallback 主檔
                └── _archive/                    舊版 v15/v16/htm
05_pipeline/    Python 轉檔流程
                ├── build_graph.py               csv → nodes.json/rels.json
                ├── precompute_questions.py      個性比例與 traits
                └── tests/                       unittest
docs/           設計文件與 spec
├── superpowers/specs/    當前設計規格
├── superpowers/plans/    實作計畫
└── spec_sanguo_v*.md     歷史 spec
```

## 開始使用

### 前端瀏覽

打開根目錄 `三國演義探險地圖.html`，會自動轉址到當前主檔。

### Pipeline 重新產生 JSON 資料

```bash
python3 05_pipeline/build_graph.py
python3 05_pipeline/precompute_questions.py
```
產出在 `03_graphrag/nodes.json`、`rels.json`、`character_personality.json`。

### 跑測試

```bash
python3 -m unittest discover -s 05_pipeline/tests -v
```

需要 Python 3.9+，無外部依賴（只用標準庫）。

## 設計

當前設計脈絡（合併 v18+ 之後）：

- `docs/superpowers/specs/2026-05-23-sanguo-character-codex-design.md` — 整站結構、出題引擎、資料模型
- `docs/superpowers/specs/2026-05-23-sanguo-character-codex-interface-spec.md` — 三主題視覺、桌面與手機 layout、兒童 a11y

歷史 spec 在 `docs/spec_sanguo_v14.md` ~ `spec_sanguo_v17.md` 保留供參。

## 授權

見 `LICENSE`。
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for phase-1 three-layer structure

更新成 source → pipeline → app 三層架構說明，加入 build
與測試指令，並指向當前設計 spec 與歷史 spec 位置。"
```

---

## Task 7: 加 `05_pipeline/README.md` 與 final integration check

**Files:**
- Create: `05_pipeline/README.md`

- [ ] **Step 1: 寫 pipeline README**

Create `05_pipeline/README.md`：

```markdown
# 05_pipeline — GraphRAG → JSON 轉檔流程

把 `03_graphrag/` 的 v3 CSV 資料轉成前端可 fetch 的 JSON。

## 跑法

```bash
# 從專案根目錄
python3 05_pipeline/build_graph.py
python3 05_pipeline/precompute_questions.py
```

## 腳本

| 檔案 | 輸入 | 輸出 |
|---|---|---|
| `build_graph.py` | `03_graphrag/sanguo_v3_nodes.csv` `relationships.csv` | `03_graphrag/nodes.json` `rels.json` |
| `precompute_questions.py` | `nodes.json` `rels.json` | `03_graphrag/character_personality.json` |

### build_graph.py

- 把 csv 內 `;` 分隔字串轉成 array（chapters）、`|` 分隔轉成 array（aliases）
- 數字欄位轉成 int / float
- 輸出 UTF-8 prettified JSON

### precompute_questions.py

對每個 `kind=entity` 且 `type=character` 的人物：
- 統計 outgoing relationship 的 category 比例
- 套用閾值產出 traits 標籤（主 spec § 6 個性配對）

## 測試

```bash
python3 -m unittest discover -s 05_pipeline/tests -v
```

需要 Python 3.9+，無外部依賴。
```

- [ ] **Step 2: 跑 final integration check**

```bash
echo "=== 目錄結構 ===" && tree -L 2 -I "01_source|02_chapters|extract|embeddings|prompts|unified|01_source|venv" 2>/dev/null || ls -la
echo "=== Phase 1 產出檔案 ===" && ls -la 03_graphrag/*.csv 03_graphrag/*.json 05_pipeline/*.py 三國演義探險地圖.html
echo "=== 跑所有測試 ===" && python3 -m unittest discover -s 05_pipeline/tests -v 2>&1 | tail -5
echo "=== Git status 應乾淨 ===" && git status
```

Expected：
- 03_graphrag/ 有 3 csv + 3 json
- 05_pipeline/ 有 2 .py + tests/
- 根目錄轉址 HTML 存在
- 15 tests pass
- git status clean

- [ ] **Step 3: Commit**

```bash
git add 05_pipeline/README.md
git commit -m "docs(pipeline): add 05_pipeline/README.md"
git log --oneline -8
```
Expected：Phase 1 共約 6-7 個 commit，可看到完整故事線。

---

## Phase 1 完成檢查清單

跑完所有 task 後，逐項勾選：

- [ ] `03_graphrag/sanguo_v3_nodes.csv` 存在 ≈ 1535 行
- [ ] `03_graphrag/sanguo_v3_relationships.csv` 存在 ≈ 6616 行
- [ ] `03_graphrag/metadata.json` 存在
- [ ] `03_graphrag/nodes.json` 存在含 1534 筆人物 / 事件 / 地點
- [ ] `03_graphrag/rels.json` 存在含 6615 筆關係
- [ ] `03_graphrag/character_personality.json` 存在，曹操有 traits
- [ ] `05_pipeline/build_graph.py` 可獨立執行
- [ ] `05_pipeline/precompute_questions.py` 可獨立執行
- [ ] `python3 -m unittest discover -s 05_pipeline/tests -v` 15 tests pass
- [ ] `04_app/_archive/` 內含 v15/v16/htm
- [ ] `04_app/三國演義探險地圖_v17.html` 仍存在（fallback）
- [ ] 根目錄 `三國演義探險地圖.html` < 2 KB 且能自動轉址到 v17
- [ ] `README.md` 反映新三層結構
- [ ] `05_pipeline/README.md` 有 pipeline 使用說明
- [ ] git history 乾淨、可看出每 task 的提交意圖

## 為 Phase 2 鋪好的基礎

Phase 1 完成後，下列工作就成為可能：

- 前端可用 `fetch('03_graphrag/nodes.json')` 載入圖譜
- 出題引擎可從 `character_personality.json` 取 traits 出題
- 新前端開發都在 `04_app/` 下，不會動到資料層
- 任何 csv schema 變更都可用 pipeline 重產 JSON，HTML 不用 rebuild

## Phase 2 / 3 預告（不在本 plan 範圍）

- **Phase 2 — 核心應用重構 + 引擎 + 三大區塊骨架**：寫 `04_app/index.html`、`app.js`、`engine.js`、五題型 UI、localStorage 進度。Phase 2 plan 由 `superpowers:writing-plans` 在 Phase 1 完成 verify 後另開。
- **Phase 3 — 視覺主題切換 + 友善設計 + a11y polish**：三主題 CSS、onboarding、卡關保護、慶祝動畫、reduce-motion fallback、兒童對比強化。Phase 3 plan 在 Phase 2 完成 verify 後另開。
