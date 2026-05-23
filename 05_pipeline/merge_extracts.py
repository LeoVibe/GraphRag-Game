#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTRACT_DIR = REPO_ROOT / "03_graphrag" / "extract"
DEFAULT_V3_NODES_CSV = REPO_ROOT / "03_graphrag" / "sanguo_v3_nodes.csv"
DEFAULT_V3_RELS_CSV = REPO_ROOT / "03_graphrag" / "sanguo_v3_relationships.csv"
DEFAULT_NODES_OUT = REPO_ROOT / "03_graphrag" / "nodes.json"
DEFAULT_RELS_OUT = REPO_ROOT / "03_graphrag" / "rels.json"

TYPE_LABEL = {
    "character": "人物",
    "location": "地點",
    "title": "稱號",
    "strategy": "計策",
    "object": "物件",
    "army": "軍隊",
    "event": "事件",
    "faction": "陣營",
    "battle": "戰役",
}

CATEGORY_LABEL = {
    "command": "陣營統率",
    "military": "軍事衝突",
    "strategy": "謀略",
    "kinship": "親族",
    "place": "地點",
    "office": "官職",
    "object": "物件",
    "story": "故事連結",
    "other": "其他",
}

CAMP_FALLBACK = {
    # 蜀漢核心（強制覆蓋 v3 csv 標 mixed 的）
    "劉備": ("shu", "劉蜀"),
    "關羽": ("shu", "劉蜀"),
    "張飛": ("shu", "劉蜀"),
    "趙雲": ("shu", "劉蜀"),
    "諸葛亮": ("shu", "劉蜀"),
    "龐統": ("shu", "劉蜀"),
    "魏延": ("shu", "劉蜀"),
    "馬超": ("shu", "劉蜀"),
    "黃忠": ("shu", "劉蜀"),
    "法正": ("shu", "劉蜀"),
    "馬岱": ("shu", "劉蜀"),
    "孫乾": ("shu", "劉蜀"),
    "糜竺": ("shu", "劉蜀"),
    "糜芳": ("shu", "劉蜀"),
    "簡雍": ("shu", "劉蜀"),
    "廖化": ("shu", "劉蜀"),
    "劉禪": ("shu", "劉蜀"),
    "關平": ("shu", "劉蜀"),
    "劉封": ("shu", "劉蜀"),
    "徐庶": ("shu", "劉蜀"),
    # 東吳核心
    "孫權": ("wu", "東吳"),
    "孫策": ("wu", "東吳"),
    "孫堅": ("wu", "東吳"),
    "周瑜": ("wu", "東吳"),
    "魯肅": ("wu", "東吳"),
    "甘寧": ("wu", "東吳"),
    "呂蒙": ("wu", "東吳"),
    "陸遜": ("wu", "東吳"),
    "黃蓋": ("wu", "東吳"),
    "程普": ("wu", "東吳"),
    "太史慈": ("wu", "東吳"),
    "韓當": ("wu", "東吳"),
    "周泰": ("wu", "東吳"),
    "蔣欽": ("wu", "東吳"),
    "張昭": ("wu", "東吳"),
    "諸葛瑾": ("wu", "東吳"),
    # 曹魏核心
    "司馬懿": ("wei", "曹魏"),
    "于禁": ("wei", "曹魏"),
    "曹丕": ("wei", "曹魏"),
    "曹植": ("wei", "曹魏"),
    "張郃": ("wei", "曹魏"),
    "徐晃": ("wei", "曹魏"),
    "夏侯惇": ("wei", "曹魏"),
    "夏侯淵": ("wei", "曹魏"),
    "曹仁": ("wei", "曹魏"),
    "曹洪": ("wei", "曹魏"),
    "許褚": ("wei", "曹魏"),
    "張遼": ("wei", "曹魏"),
    "荀彧": ("wei", "曹魏"),
    "荀攸": ("wei", "曹魏"),
    "郭嘉": ("wei", "曹魏"),
    "賈詡": ("wei", "曹魏"),
    "李典": ("wei", "曹魏"),
    "樂進": ("wei", "曹魏"),
    "典韋": ("wei", "曹魏"),
    "程昱": ("wei", "曹魏"),
    "滿寵": ("wei", "曹魏"),
}

GENERIC_ALIAS_TOKENS = {
    "主公",
    "丞相",
    "將軍",
    "大將",
    "都督",
    "大都督",
    "先生",
    "使君",
    "天子",
    "皇帝",
    "帝",
    "陛下",
    "太后",
    "皇后",
    "百官",
    "公卿",
    "朝廷",
    "社稷",
    "漢室",
    "漢朝",
    "江東",
    "江南",
    "荊州",
    "徐州",
    "城中",
    "城內",
    "軍士",
    "士卒",
    "兵馬",
    "水軍",
    "戰船",
    "船隻",
    "糧草",
    "書信",
    "書",
    "印綬",
    "寶劍",
    "百姓",
}


def _variant_token(raw: str) -> str:
    return raw.replace("於", "于")


class DisjointSet:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, item: int) -> int:
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1


def _clean_token(raw: Any) -> str:
    return str(raw or "").strip()


def _unique_preserve(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = _clean_token(value)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _identity_tokens(values: list[str]) -> list[str]:
    tokens: list[str] = []
    for value in _unique_preserve(values):
        tokens.append(value)
        variant = _variant_token(value)
        if variant != value:
            tokens.append(variant)
    return _unique_preserve(tokens)


def _description_parts(raw: Any) -> list[str]:
    text = _clean_token(raw)
    if not text:
        return []
    return [
        part.strip()
        for part in re.split(r"[；;]+", text)
        if part and part.strip()
    ]


def _chapter_from_path(path: Path) -> int:
    match = re.search(r"c(\d+)_graph\.json$", path.name)
    if not match:
        return 0
    return int(match.group(1))


def _read_extract_records(extract_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entity_records: list[dict[str, Any]] = []
    rel_records: list[dict[str, Any]] = []
    pattern = str(extract_dir / "c0??_graph.json")
    for filename in sorted(glob.glob(pattern)):
        path = Path(filename)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        chapter_no = int(data.get("chapter_no") or _chapter_from_path(path))
        for entity in data.get("entities", []):
            local_id = _clean_token(entity.get("id"))
            if not local_id:
                continue
            entity_records.append(
                {
                    "chapter_no": chapter_no,
                    "local_id": local_id,
                    "name": _clean_token(entity.get("name")),
                    "type": _clean_token(entity.get("type")) or "other",
                    "aliases": _unique_preserve(list(entity.get("aliases") or [])),
                    "description": _clean_token(entity.get("description")),
                }
            )
        for rel in data.get("relationships", []):
            rel_records.append(
                {
                    "chapter_no": chapter_no,
                    "source": _clean_token(rel.get("source")),
                    "target": _clean_token(rel.get("target")),
                    "type": _clean_token(rel.get("type")),
                    "description": _clean_token(rel.get("description")),
                    "confidence": _to_float(rel.get("confidence"), 0.0),
                }
            )
    return entity_records, rel_records


def _to_float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _union_by_identity(records: list[dict[str, Any]]) -> DisjointSet:
    dsu = DisjointSet(len(records))
    by_name: dict[str, list[int]] = defaultdict(list)
    token_by_type: dict[tuple[str, str], list[int]] = defaultdict(list)
    name_types: dict[str, set[str]] = defaultdict(set)

    for index, record in enumerate(records):
        name = record["name"]
        record_type = record["type"]
        if name:
            by_name[name].append(index)
            for token in _identity_tokens([name]):
                name_types[token].add(record_type)
        for token in _identity_tokens([name] + record["aliases"]):
            token_by_type[(token, record_type)].append(index)

    for indexes in by_name.values():
        first = indexes[0]
        for index in indexes[1:]:
            dsu.union(first, index)

    for (token, record_type), indexes in token_by_type.items():
        if not _is_safe_alias_token(token, record_type, indexes, records, name_types):
            continue
        first = indexes[0]
        for index in indexes[1:]:
            dsu.union(first, index)

    return dsu


def _is_safe_alias_token(
    token: str,
    record_type: str,
    indexes: list[int],
    records: list[dict[str, Any]],
    name_types: dict[str, set[str]],
) -> bool:
    if not token or len(token) <= 1 or token in GENERIC_ALIAS_TOKENS:
        return False
    if record_type in name_types.get(token, set()):
        return True
    distinct_names = {records[index]["name"] for index in indexes if records[index]["name"]}
    return len(distinct_names) <= 2


def _choose_most_frequent(values: list[str], default: str = "other") -> str:
    counter = Counter(value for value in values if value)
    if not counter:
        return default
    return sorted(counter.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))[0][0]


def _choose_canonical_name(records: list[dict[str, Any]]) -> str:
    names = [record["name"] for record in records]
    fallback_names = [name for name in names if name in CAMP_FALLBACK]
    if fallback_names:
        return _choose_most_frequent(fallback_names, "")
    return _choose_most_frequent(names, "")


def _read_camp_lookup(nodes_csv: Path) -> dict[str, tuple[str, str]]:
    lookup: dict[str, tuple[str, str]] = {}
    with open(nodes_csv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = _clean_token(row.get("name"))
            if not name:
                continue
            lookup[name] = (
                _clean_token(row.get("camp")) or "other",
                _clean_token(row.get("campLabel")) or "其他",
            )
    return lookup


def _entity_id_to_name(entity_id: str) -> str:
    if "_" not in entity_id:
        return entity_id
    return entity_id.split("_", 1)[1]


def _read_category_lookup(rels_csv: Path) -> dict[tuple[str, str, str], str]:
    lookup: dict[tuple[str, str, str], str] = {}
    with open(rels_csv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            source_name = _entity_id_to_name(_clean_token(row.get("source")))
            target_name = _entity_id_to_name(_clean_token(row.get("target")))
            relation_type = _clean_token(row.get("relationType"))
            category = _clean_token(row.get("category"))
            if source_name and target_name and relation_type and category:
                lookup[(source_name, target_name, relation_type)] = category
    return lookup


def _derive_category(
    source_name: str,
    target_name: str,
    relation_type: str,
    category_lookup: dict[tuple[str, str, str], str],
) -> str:
    category = category_lookup.get((source_name, target_name, relation_type))
    if category:
        return category
    rules = [
        ("kinship", "結拜兄弟父母子女夫妻族姻"),
        ("military", "攻戰敗破殺俘伐討擒"),
        ("command", "事從降封屬統"),
        ("command", ("部下", "麾下")),
        ("strategy", "計策騙智謀"),
        ("strategy", ("獻策", "設計")),
        ("place", "治守在住居處"),
        ("office", "任官職賜"),
        ("office", ("拜為",)),
    ]
    for rule_category, needles in rules:
        if isinstance(needles, tuple):
            if any(needle in relation_type for needle in needles):
                return rule_category
        elif any(needle in relation_type for needle in needles):
            return rule_category
    return "story"


def _build_entities(
    entity_records: list[dict[str, Any]],
    dsu: DisjointSet,
    camp_lookup: dict[str, tuple[str, str]],
) -> tuple[list[dict[str, Any]], dict[tuple[int, str], str], dict[str, str]]:
    grouped_indexes: dict[int, list[int]] = defaultdict(list)
    for index in range(len(entity_records)):
        grouped_indexes[dsu.find(index)].append(index)

    nodes: list[dict[str, Any]] = []
    local_to_unified: dict[tuple[int, str], str] = {}
    id_to_name: dict[str, str] = {}

    for indexes in grouped_indexes.values():
        records = [entity_records[index] for index in indexes]
        canonical_name = _choose_canonical_name(records)
        entity_type = _choose_most_frequent([record["type"] for record in records])
        if not canonical_name:
            continue

        unified_id = f"entity:{entity_type}_{canonical_name}"
        chapters = sorted({int(record["chapter_no"]) for record in records})
        alias_values: list[str] = []
        description_values: list[str] = []
        for record in records:
            alias_values.append(record["name"])
            alias_values.extend(record["aliases"])
            description_values.extend(_description_parts(record["description"]))
            local_to_unified[(int(record["chapter_no"]), record["local_id"])] = unified_id

        aliases = [alias for alias in _unique_preserve(alias_values) if alias != canonical_name]
        description = "；".join(_unique_preserve(description_values))
        camp, camp_label = CAMP_FALLBACK.get(
            canonical_name,
            camp_lookup.get(canonical_name, ("other", "其他")),
        )
        node = {
            "id": unified_id,
            "name": canonical_name,
            "type": entity_type,
            "typeLabel": TYPE_LABEL.get(entity_type, "其他"),
            "kind": "entity",
            "camp": camp,
            "campLabel": camp_label,
            "chapters": chapters,
            "chapterStart": min(chapters),
            "chapterEnd": max(chapters),
            "chapterCount": len(chapters),
            "degree": 0,
            "score": 0,
            "isTrunk": False,
            "aliases": aliases,
            "description": description,
        }
        nodes.append(node)
        id_to_name[unified_id] = canonical_name

    return nodes, local_to_unified, id_to_name


def _build_relationships(
    rel_records: list[dict[str, Any]],
    local_to_unified: dict[tuple[int, str], str],
    id_to_name: dict[str, str],
    category_lookup: dict[tuple[str, str, str], str],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in rel_records:
        chapter_no = int(record["chapter_no"])
        source = local_to_unified.get((chapter_no, record["source"]))
        target = local_to_unified.get((chapter_no, record["target"]))
        if not source or not target:
            print(
                "WARNING: skipping unmappable relationship "
                f"chapter={chapter_no} source={record['source']} target={record['target']}",
                file=sys.stderr,
            )
            continue
        relation_type = record["type"]
        key = (source, target, relation_type)
        if key not in grouped:
            grouped[key] = {
                "source": source,
                "target": target,
                "relationType": relation_type,
                "chapters": set(),
                "weight": 0,
                "confidence": 0.0,
                "descriptionParts": [],
            }
        item = grouped[key]
        item["chapters"].add(chapter_no)
        item["weight"] += 1
        item["confidence"] = max(item["confidence"], _to_float(record["confidence"], 0.0))
        item["descriptionParts"].extend(_description_parts(record["description"]))

    rels: list[dict[str, Any]] = []
    for item in grouped.values():
        chapters = sorted(item["chapters"])
        source_name = id_to_name.get(item["source"], _entity_id_to_name(item["source"]))
        target_name = id_to_name.get(item["target"], _entity_id_to_name(item["target"]))
        category = _derive_category(
            source_name,
            target_name,
            item["relationType"],
            category_lookup,
        )
        rels.append(
            {
                "source": item["source"],
                "target": item["target"],
                "relationType": item["relationType"],
                "category": category,
                "categoryLabel": CATEGORY_LABEL.get(category, "其他"),
                "chapters": chapters,
                "chapterStart": min(chapters),
                "chapterEnd": max(chapters),
                "weight": item["weight"],
                "confidence": float(item["confidence"]),
                "description": "；".join(_unique_preserve(item["descriptionParts"])),
                "kind": "entity_relation",
            }
        )

    rels.sort(
        key=lambda rel: (
            rel["chapterStart"],
            id_to_name.get(rel["source"], rel["source"]),
            id_to_name.get(rel["target"], rel["target"]),
            rel["relationType"],
        )
    )
    for index, rel in enumerate(rels, start=1):
        rel["id"] = f"rel:{index:06d}"
    return rels


def _apply_degrees(nodes: list[dict[str, Any]], rels: list[dict[str, Any]]) -> None:
    degree_by_id: dict[str, set[str]] = defaultdict(set)
    for rel in rels:
        degree_by_id[rel["source"]].add(rel["id"])
        degree_by_id[rel["target"]].add(rel["id"])
    for node in nodes:
        degree = len(degree_by_id.get(node["id"], set()))
        chapter_count = len(node["chapters"])
        node["degree"] = degree
        node["score"] = degree * chapter_count
        node["isTrunk"] = degree >= 10 or chapter_count >= 10


def build(
    extract_dir: Path = DEFAULT_EXTRACT_DIR,
    v3_nodes_csv: Path = DEFAULT_V3_NODES_CSV,
    v3_rels_csv: Path = DEFAULT_V3_RELS_CSV,
    nodes_out: Path = DEFAULT_NODES_OUT,
    rels_out: Path = DEFAULT_RELS_OUT,
) -> None:
    entity_records, rel_records = _read_extract_records(Path(extract_dir))
    dsu = _union_by_identity(entity_records)
    camp_lookup = _read_camp_lookup(Path(v3_nodes_csv))
    category_lookup = _read_category_lookup(Path(v3_rels_csv))
    nodes, local_to_unified, id_to_name = _build_entities(entity_records, dsu, camp_lookup)
    rels = _build_relationships(rel_records, local_to_unified, id_to_name, category_lookup)
    _apply_degrees(nodes, rels)
    nodes.sort(key=lambda node: (node["chapterStart"], node["type"], node["name"]))

    Path(nodes_out).parent.mkdir(parents=True, exist_ok=True)
    with open(nodes_out, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)
    with open(rels_out, "w", encoding="utf-8") as f:
        json.dump(rels, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(nodes)} nodes to {nodes_out}", file=sys.stderr)
    print(f"wrote {len(rels)} relationships to {rels_out}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract-dir", type=Path, default=DEFAULT_EXTRACT_DIR)
    parser.add_argument("--v3-nodes-csv", type=Path, default=DEFAULT_V3_NODES_CSV)
    parser.add_argument("--v3-rels-csv", type=Path, default=DEFAULT_V3_RELS_CSV)
    parser.add_argument("--nodes-out", type=Path, default=DEFAULT_NODES_OUT)
    parser.add_argument("--rels-out", type=Path, default=DEFAULT_RELS_OUT)
    args = parser.parse_args()
    build(
        extract_dir=args.extract_dir,
        v3_nodes_csv=args.v3_nodes_csv,
        v3_rels_csv=args.v3_rels_csv,
        nodes_out=args.nodes_out,
        rels_out=args.rels_out,
    )


if __name__ == "__main__":
    main()
