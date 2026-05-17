#!/usr/bin/env python3
"""Merge per-chapter Sanguo graph JSON into unified entity and relationship tables."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


GENERATED_MARKER = ".generated-by-merge_sanguo_graph"

GENERIC_ALIAS_TOKENS = {
    "",
    "之",
    "其",
    "他",
    "公",
    "王",
    "帝",
    "君",
    "兵",
    "軍",
    "賊",
    "眾",
    "官",
    "將",
    "太子",
    "皇帝",
    "天子",
    "今上",
    "皇后",
    "太后",
    "大將軍",
    "中郎將",
    "太尉",
    "刺史",
    "太守",
    "關張",
}

PREFERRED_NAMES = {
    "關公": "關羽",
    "雲長": "關羽",
    "長生": "關羽",
    "玄德": "劉備",
    "翼德": "張飛",
    "張翼德": "張飛",
    "何後": "何太后",
    "許韶": "許劭",
}


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self.parent[root_right] = root_left


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[\s　「」『』“”‘’\"'`、，。；：:;,.!?！？（）()\[\]【】《》〈〉]", "", value)
    return value.strip()


def preferred_name(value: str) -> str:
    return PREFERRED_NAMES.get(value, value)


def merge_token(value: str) -> str | None:
    value = preferred_name(normalize_text(value))
    if value in GENERIC_ALIAS_TOKENS:
        return None
    if len(value) <= 1:
        return None
    return value


def stable_unique(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    output: list[Any] = []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            output.append(value)
    return output


def reset_output_dir(path: Path, force: bool) -> None:
    if not path.exists():
        return
    marker = path / GENERATED_MARKER
    if not force:
        raise SystemExit(f"Output already exists: {path}. Re-run with --force.")
    if not marker.exists():
        raise SystemExit(f"Refusing to replace {path}; generated marker is missing.")
    shutil.rmtree(path)


def read_graphs(input_dirs: list[Path], start_chapter: int | None, end_chapter: int | None) -> list[dict[str, Any]]:
    graphs: list[dict[str, Any]] = []
    seen_chapters: dict[int, str] = {}
    for input_dir in input_dirs:
        for path in sorted(input_dir.glob("c*_graph.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            chapter_no = int(data["chapter_no"])
            if start_chapter is not None and chapter_no < start_chapter:
                continue
            if end_chapter is not None and chapter_no > end_chapter:
                continue
            if chapter_no in seen_chapters:
                raise SystemExit(
                    f"Duplicate chapter {chapter_no}: {seen_chapters[chapter_no]} and {path.as_posix()}"
                )
            seen_chapters[chapter_no] = path.as_posix()
            data["_path"] = path.as_posix()
            graphs.append(data)
    if not graphs:
        input_label = ", ".join(path.as_posix() for path in input_dirs)
        raise SystemExit(f"No c*_graph.json files found in {input_label}")
    return sorted(graphs, key=lambda graph: int(graph["chapter_no"]))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def entity_ref(chapter_no: int, entity_id: str) -> str:
    return f"c{chapter_no:03d}:{entity_id}"


def collect_raw_entities(graphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for graph in graphs:
        chapter_no = graph["chapter_no"]
        for entity in graph["entities"]:
            rows.append(
                {
                    "raw_ref": entity_ref(chapter_no, entity["id"]),
                    "chapter_no": chapter_no,
                    "chapter_title": graph["chapter_title"],
                    **entity,
                }
            )
    return rows


def build_entity_groups(raw_entities: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    refs = [entity["raw_ref"] for entity in raw_entities]
    uf = UnionFind(refs)
    merge_reasons: list[dict[str, Any]] = []

    by_generated_id: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_token: dict[tuple[str, str], list[str]] = defaultdict(list)

    for entity in raw_entities:
        by_generated_id[(entity["type"], entity["id"])].append(entity["raw_ref"])
        name_token = merge_token(entity["name"])
        if name_token:
            by_name[(entity["type"], name_token)].append(entity["raw_ref"])
            by_token[(entity["type"], name_token)].append(entity["raw_ref"])
        for alias in entity.get("aliases", []):
            token = merge_token(alias)
            if token:
                by_token[(entity["type"], token)].append(entity["raw_ref"])

    def union_refs(refs_to_union: list[str], reason: str, key: str) -> None:
        unique_refs = sorted(set(refs_to_union))
        if len(unique_refs) < 2:
            return
        first = unique_refs[0]
        for other in unique_refs[1:]:
            uf.union(first, other)
        merge_reasons.append({"reason": reason, "key": key, "raw_refs": unique_refs})

    for (entity_type, generated_id), refs_for_key in by_generated_id.items():
        union_refs(refs_for_key, "same_generated_id", f"{entity_type}:{generated_id}")
    for (entity_type, name), refs_for_key in by_name.items():
        union_refs(refs_for_key, "same_type_and_name", f"{entity_type}:{name}")
    for (entity_type, token), refs_for_key in by_token.items():
        union_refs(refs_for_key, "same_type_name_or_alias", f"{entity_type}:{token}")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_ref = {entity["raw_ref"]: entity for entity in raw_entities}
    for ref in refs:
        groups[uf.find(ref)].append(by_ref[ref])

    return groups, merge_reasons


def choose_canonical_name(group: list[dict[str, Any]]) -> str:
    candidates: list[str] = []
    for entity in group:
        candidates.append(preferred_name(normalize_text(entity["name"])))
        for alias in entity.get("aliases", []):
            token = merge_token(alias)
            if token:
                candidates.append(token)
    counts = Counter(candidates)
    if not counts:
        return group[0]["name"]
    first_seen = {candidate: index for index, candidate in enumerate(candidates)}
    return sorted(counts, key=lambda item: (-counts[item], first_seen[item], item))[0]


def build_unified_entities(groups: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    unified_entities: list[dict[str, Any]] = []
    raw_to_unified: dict[str, str] = {}
    merge_decisions: list[dict[str, Any]] = []

    sorted_groups = sorted(groups.values(), key=lambda group: min((entity["chapter_no"], entity["id"]) for entity in group))
    for index, group in enumerate(sorted_groups, start=1):
        unified_id = f"ent_{index:04d}"
        entity_type = Counter(entity["type"] for entity in group).most_common(1)[0][0]
        canonical_name = choose_canonical_name(group)
        aliases = stable_unique(
            [
                preferred_name(normalize_text(value))
                for entity in group
                for value in [entity["name"], *entity.get("aliases", [])]
                if merge_token(value)
            ]
        )
        aliases = [alias for alias in aliases if alias != canonical_name]
        descriptions = stable_unique(
            [
                {"chapter_no": entity["chapter_no"], "text": entity["description"]}
                for entity in group
                if entity.get("description")
            ]
        )
        evidence = stable_unique(
            [
                {"chapter_no": entity["chapter_no"], "text": text}
                for entity in group
                for text in entity.get("evidence", [])
                if text
            ]
        )
        raw_refs = sorted(entity["raw_ref"] for entity in group)
        chapters = sorted({entity["chapter_no"] for entity in group})

        for raw_ref in raw_refs:
            raw_to_unified[raw_ref] = unified_id

        unified_entities.append(
            {
                "unified_id": unified_id,
                "name": canonical_name,
                "type": entity_type,
                "aliases": aliases,
                "chapters": chapters,
                "source_entity_count": len(group),
                "raw_refs": raw_refs,
                "descriptions": descriptions,
                "evidence": evidence,
            }
        )
        if len(group) > 1:
            merge_decisions.append(
                {
                    "unified_id": unified_id,
                    "name": canonical_name,
                    "type": entity_type,
                    "source_entity_count": len(group),
                    "raw_entities": [
                        {
                            "raw_ref": entity["raw_ref"],
                            "chapter_no": entity["chapter_no"],
                            "id": entity["id"],
                            "name": entity["name"],
                            "type": entity["type"],
                            "aliases": entity.get("aliases", []),
                        }
                        for entity in group
                    ],
                }
            )

    return unified_entities, raw_to_unified, merge_decisions


def build_unified_relationships(
    graphs: list[dict[str, Any]],
    raw_to_unified: dict[str, str],
    unified_entities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entity_by_id = {entity["unified_id"]: entity for entity in unified_entities}
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    dropped: list[dict[str, Any]] = []

    for graph in graphs:
        chapter_no = graph["chapter_no"]
        for relationship in graph["relationships"]:
            source_ref = entity_ref(chapter_no, relationship["source"])
            target_ref = entity_ref(chapter_no, relationship["target"])
            source_unified = raw_to_unified.get(source_ref)
            target_unified = raw_to_unified.get(target_ref)
            if not source_unified or not target_unified:
                dropped.append(
                    {
                        "reason": "missing_entity_ref",
                        "chapter_no": chapter_no,
                        "relationship": relationship,
                    }
                )
                continue
            if source_unified == target_unified:
                dropped.append(
                    {
                        "reason": "self_loop_after_entity_merge",
                        "chapter_no": chapter_no,
                        "relationship": relationship,
                    }
                )
                continue
            relation_type = normalize_text(relationship["type"])
            grouped[(source_unified, target_unified, relation_type)].append({"chapter_no": chapter_no, **relationship})

    unified_relationships: list[dict[str, Any]] = []
    for index, ((source, target, relation_type), rows) in enumerate(
        sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])),
        start=1,
    ):
        confidences = [float(row.get("confidence", 0)) for row in rows]
        descriptions = stable_unique(
            [
                {"chapter_no": row["chapter_no"], "text": row["description"]}
                for row in rows
                if row.get("description")
            ]
        )
        evidence = stable_unique(
            [
                {"chapter_no": row["chapter_no"], "text": text}
                for row in rows
                for text in row.get("evidence", [])
                if text
            ]
        )
        unified_relationships.append(
            {
                "relationship_id": f"rel_{index:04d}",
                "source": source,
                "source_name": entity_by_id[source]["name"],
                "target": target,
                "target_name": entity_by_id[target]["name"],
                "type": relation_type,
                "chapters": sorted({row["chapter_no"] for row in rows}),
                "source_relationship_count": len(rows),
                "confidence_max": max(confidences) if confidences else None,
                "confidence_avg": round(sum(confidences) / len(confidences), 4) if confidences else None,
                "descriptions": descriptions,
                "evidence": evidence,
                "raw_relationships": [
                    {
                        "chapter_no": row["chapter_no"],
                        "source": row["source"],
                        "target": row["target"],
                        "type": row["type"],
                    }
                    for row in rows
                ],
            }
        )

    return unified_relationships, dropped


def find_cross_type_name_candidates(raw_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in raw_entities:
        token = merge_token(entity["name"])
        if token:
            by_name[token].append(entity)
    candidates: list[dict[str, Any]] = []
    for name, rows in sorted(by_name.items()):
        types = sorted({row["type"] for row in rows})
        if len(types) > 1:
            candidates.append(
                {
                    "name": name,
                    "types": types,
                    "raw_entities": [
                        {
                            "raw_ref": row["raw_ref"],
                            "chapter_no": row["chapter_no"],
                            "id": row["id"],
                            "name": row["name"],
                            "type": row["type"],
                        }
                        for row in rows
                    ],
                }
            )
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        action="append",
        default=None,
        help="Input directory containing c*_graph.json. May be passed multiple times.",
    )
    parser.add_argument(
        "--start-chapter",
        type=int,
        help="Inclusive chapter start filter.",
    )
    parser.add_argument(
        "--end-chapter",
        type=int,
        help="Inclusive chapter end filter.",
    )
    parser.add_argument(
        "--report-title",
        default="三國演義 Unified Graph",
        help="README title for this merge output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_ref/sanguo_chaptered/unified_graph_codex_gpt-5.5_first3"),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.start_chapter is not None and args.end_chapter is not None and args.start_chapter > args.end_chapter:
        raise SystemExit("--start-chapter must be <= --end-chapter")

    reset_output_dir(args.output, args.force)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / GENERATED_MARKER).write_text("generated\n", encoding="utf-8")

    input_dirs = args.input_dir or [Path("data_ref/sanguo_chaptered/graph_extract_codex_gpt-5.5_first3")]
    graphs = read_graphs(input_dirs, args.start_chapter, args.end_chapter)
    chapter_numbers = [int(graph["chapter_no"]) for graph in graphs]
    raw_entities = collect_raw_entities(graphs)
    groups, merge_reasons = build_entity_groups(raw_entities)
    unified_entities, raw_to_unified, merge_decisions = build_unified_entities(groups)
    unified_relationships, dropped_relationships = build_unified_relationships(graphs, raw_to_unified, unified_entities)
    cross_type_candidates = find_cross_type_name_candidates(raw_entities)

    raw_entity_mapping = [
        {"raw_ref": raw_ref, "unified_id": unified_id}
        for raw_ref, unified_id in sorted(raw_to_unified.items())
    ]

    write_jsonl(args.output / "unified_entities.jsonl", unified_entities)
    write_jsonl(args.output / "unified_relationships.jsonl", unified_relationships)
    write_jsonl(args.output / "raw_entity_to_unified.jsonl", raw_entity_mapping)
    write_jsonl(args.output / "merge_decisions.jsonl", merge_decisions)
    write_jsonl(args.output / "merge_reasons.jsonl", merge_reasons)
    write_jsonl(args.output / "dropped_relationships.jsonl", dropped_relationships)
    write_jsonl(args.output / "cross_type_name_candidates.jsonl", cross_type_candidates)

    raw_relationship_count = sum(len(graph["relationships"]) for graph in graphs)
    summary = {
        "input_dirs": [input_dir.as_posix() for input_dir in input_dirs],
        "output": args.output.as_posix(),
        "chapter_count": len(graphs),
        "chapter_start": min(chapter_numbers),
        "chapter_end": max(chapter_numbers),
        "chapter_numbers": chapter_numbers,
        "raw_entity_count": len(raw_entities),
        "unified_entity_count": len(unified_entities),
        "merged_entity_count_delta": len(raw_entities) - len(unified_entities),
        "merge_group_count": len(merge_decisions),
        "raw_relationship_count": raw_relationship_count,
        "unified_relationship_count": len(unified_relationships),
        "deduped_relationship_count_delta": raw_relationship_count - len(unified_relationships) - len(dropped_relationships),
        "dropped_relationship_count": len(dropped_relationships),
        "cross_type_name_candidate_count": len(cross_type_candidates),
    }
    (args.output / "merge_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_lines = [
        f"# {args.report_title}",
        "",
        f"- Input dirs: `{', '.join(input_dir.as_posix() for input_dir in input_dirs)}`",
        f"- Chapters: `{min(chapter_numbers)}` to `{max(chapter_numbers)}`",
        f"- Raw entities: `{summary['raw_entity_count']}`",
        f"- Unified entities: `{summary['unified_entity_count']}`",
        f"- Merged entity delta: `{summary['merged_entity_count_delta']}`",
        f"- Raw relationships: `{summary['raw_relationship_count']}`",
        f"- Unified relationships: `{summary['unified_relationship_count']}`",
        f"- Deduped relationship delta: `{summary['deduped_relationship_count_delta']}`",
        f"- Dropped relationships: `{summary['dropped_relationship_count']}`",
        f"- Cross-type name candidates: `{summary['cross_type_name_candidate_count']}`",
        "",
        "## Files",
        "",
        "- `unified_entities.jsonl`",
        "- `unified_relationships.jsonl`",
        "- `raw_entity_to_unified.jsonl`",
        "- `merge_decisions.jsonl`",
        "- `merge_reasons.jsonl`",
        "- `cross_type_name_candidates.jsonl`",
        "- `dropped_relationships.jsonl`",
        "- `merge_summary.json`",
        "",
        "## Notes",
        "",
        "- Entity merge is conservative and only merges within the same entity type.",
        "- Same generated id, same normalized name, and same normalized name/alias tokens are merged.",
        "- Relationship dedupe groups by unified source, unified target, and relationship type.",
    ]
    (args.output / "README.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
