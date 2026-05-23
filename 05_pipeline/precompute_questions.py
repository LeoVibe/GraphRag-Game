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

TRAIT_THRESHOLDS = [
    ("strategy", 0.20, "會算計"),
    ("command", 0.25, "會帶人"),
    ("military", 0.30, "會打仗"),
    ("kinship", 0.10, "重感情"),
]
PERSONALITY_CATEGORIES = {category for category, _, _ in TRAIT_THRESHOLDS}


def _is_character(node: dict[str, Any]) -> bool:
    return node.get("kind") == "entity" and node.get("type") == "character"


def _compute_ratios(rels: list[dict[str, Any]], subject_id: str) -> dict[str, float]:
    counter: Counter[str] = Counter()
    for rel in rels:
        if rel["source"] == subject_id:
            category = rel.get("category", "other")
            if category in PERSONALITY_CATEGORIES:
                counter[category] += 1
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
