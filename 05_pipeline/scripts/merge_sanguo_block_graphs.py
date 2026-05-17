#!/usr/bin/env python3
"""Merge block-level Sanguo unified graphs into a larger unified graph."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from merge_sanguo_graph import (
    UnionFind,
    choose_canonical_name,
    find_cross_type_name_candidates,
    merge_token,
    normalize_text,
    stable_unique,
)


GENERATED_MARKER = ".generated-by-merge_sanguo_block_graphs"


def reset_output_dir(path: Path, force: bool) -> None:
    if not path.exists():
        return
    marker = path / GENERATED_MARKER
    if not force:
        raise SystemExit(f"Output already exists: {path}. Re-run with --force.")
    if not marker.exists():
        raise SystemExit(f"Refusing to replace {path}; generated marker is missing.")
    shutil.rmtree(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def block_label(path: Path) -> str:
    match = re.search(r"block_(\d{3})_(\d{3})", path.name)
    if match:
        return f"block_{match.group(1)}_{match.group(2)}"
    return path.name


def block_entity_ref(block: str, entity_id: str) -> str:
    return f"{block}:{entity_id}"


def block_relationship_ref(block: str, relationship_id: str) -> str:
    return f"{block}:{relationship_id}"


def collect_block_entities(block_dirs: list[Path]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    for block_dir in block_dirs:
        block = block_label(block_dir)
        for entity in read_jsonl(block_dir / "unified_entities.jsonl"):
            chapters = sorted(int(chapter) for chapter in entity.get("chapters", []))
            descriptions = entity.get("descriptions", [])
            evidence = entity.get("evidence", [])
            entities.append(
                {
                    "raw_ref": block_entity_ref(block, entity["unified_id"]),
                    "block": block,
                    "chapter_no": min(chapters) if chapters else 0,
                    "chapters": chapters,
                    "chapter_title": block,
                    "id": block_entity_ref(block, entity["unified_id"]),
                    "name": entity["name"],
                    "type": entity["type"],
                    "aliases": entity.get("aliases", []),
                    "description": " / ".join(item.get("text", "") for item in descriptions if item.get("text")),
                    "descriptions": descriptions,
                    "evidence": [item.get("text", "") for item in evidence if item.get("text")],
                    "evidence_items": evidence,
                    "block_unified_id": entity["unified_id"],
                    "source_entity_count": int(entity.get("source_entity_count", 1)),
                    "source_raw_refs": entity.get("raw_refs", []),
                }
            )
    return entities


def build_block_entity_groups(raw_entities: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    refs = [entity["raw_ref"] for entity in raw_entities]
    uf = UnionFind(refs)
    merge_reasons: list[dict[str, Any]] = []
    by_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_token: dict[tuple[str, str], list[str]] = defaultdict(list)

    for entity in raw_entities:
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
        merge_reasons.append({"reason": reason, "key": key, "block_entity_refs": unique_refs})

    for (entity_type, name), refs_for_key in by_name.items():
        union_refs(refs_for_key, "same_type_and_name", f"{entity_type}:{name}")
    for (entity_type, token), refs_for_key in by_token.items():
        union_refs(refs_for_key, "same_type_name_or_alias", f"{entity_type}:{token}")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_ref = {entity["raw_ref"]: entity for entity in raw_entities}
    for ref in refs:
        groups[uf.find(ref)].append(by_ref[ref])
    return groups, merge_reasons


def build_global_entities(groups: dict[str, list[dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    global_entities: list[dict[str, Any]] = []
    block_to_global: dict[str, str] = {}
    merge_decisions: list[dict[str, Any]] = []

    sorted_groups = sorted(groups.values(), key=lambda group: (min(min(entity["chapters"] or [0]) for entity in group), group[0]["name"]))
    for index, group in enumerate(sorted_groups, start=1):
        unified_id = f"ent_{index:05d}"
        entity_type = Counter(entity["type"] for entity in group).most_common(1)[0][0]
        canonical_name = choose_canonical_name(group)
        aliases = stable_unique(
            [
                normalize_text(value)
                for entity in group
                for value in [entity["name"], *entity.get("aliases", [])]
                if merge_token(value)
            ]
        )
        aliases = [alias for alias in aliases if alias != canonical_name]
        chapters = sorted({chapter for entity in group for chapter in entity.get("chapters", [])})
        descriptions = stable_unique(
            [
                {"block": entity["block"], **description}
                for entity in group
                for description in entity.get("descriptions", [])
                if description.get("text")
            ]
        )
        evidence = stable_unique(
            [
                {"block": entity["block"], **item}
                for entity in group
                for item in entity.get("evidence_items", [])
                if item.get("text")
            ]
        )
        block_refs = sorted(entity["raw_ref"] for entity in group)
        source_raw_refs = sorted({raw_ref for entity in group for raw_ref in entity.get("source_raw_refs", [])})
        for block_ref in block_refs:
            block_to_global[block_ref] = unified_id

        global_entities.append(
            {
                "unified_id": unified_id,
                "name": canonical_name,
                "type": entity_type,
                "aliases": aliases,
                "chapters": chapters,
                "source_block_entity_count": len(group),
                "source_raw_entity_count": sum(entity.get("source_entity_count", 1) for entity in group),
                "block_refs": block_refs,
                "raw_refs": source_raw_refs,
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
                    "source_block_entity_count": len(group),
                    "source_raw_entity_count": sum(entity.get("source_entity_count", 1) for entity in group),
                    "block_entities": [
                        {
                            "block_ref": entity["raw_ref"],
                            "block": entity["block"],
                            "chapters": entity["chapters"],
                            "id": entity["block_unified_id"],
                            "name": entity["name"],
                            "type": entity["type"],
                            "aliases": entity.get("aliases", []),
                        }
                        for entity in group
                    ],
                }
            )

    return global_entities, block_to_global, merge_decisions


def build_global_relationships(
    block_dirs: list[Path],
    block_to_global: dict[str, str],
    global_entities: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entity_by_id = {entity["unified_id"]: entity for entity in global_entities}
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    dropped: list[dict[str, Any]] = []

    for block_dir in block_dirs:
        block = block_label(block_dir)
        for relationship in read_jsonl(block_dir / "unified_relationships.jsonl"):
            source_ref = block_entity_ref(block, relationship["source"])
            target_ref = block_entity_ref(block, relationship["target"])
            source = block_to_global.get(source_ref)
            target = block_to_global.get(target_ref)
            if not source or not target:
                dropped.append({"reason": "missing_block_entity_ref", "block": block, "relationship": relationship})
                continue
            if source == target:
                dropped.append({"reason": "self_loop_after_global_entity_merge", "block": block, "relationship": relationship})
                continue
            relation_type = normalize_text(relationship["type"])
            grouped[(source, target, relation_type)].append({"block": block, **relationship})

    global_relationships: list[dict[str, Any]] = []
    for index, ((source, target, relation_type), rows) in enumerate(
        sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])),
        start=1,
    ):
        confidences = [float(row.get("confidence_avg", 0)) for row in rows if row.get("confidence_avg") is not None]
        descriptions = stable_unique(
            [
                {"block": row["block"], **description}
                for row in rows
                for description in row.get("descriptions", [])
                if description.get("text")
            ]
        )
        evidence = stable_unique(
            [
                {"block": row["block"], **item}
                for row in rows
                for item in row.get("evidence", [])
                if item.get("text")
            ]
        )
        raw_relationships = stable_unique(
            [
                {"block": row["block"], **raw}
                for row in rows
                for raw in row.get("raw_relationships", [])
            ]
        )
        global_relationships.append(
            {
                "relationship_id": f"rel_{index:05d}",
                "source": source,
                "source_name": entity_by_id[source]["name"],
                "target": target,
                "target_name": entity_by_id[target]["name"],
                "type": relation_type,
                "chapters": sorted({chapter for row in rows for chapter in row.get("chapters", [])}),
                "source_block_relationship_count": len(rows),
                "source_raw_relationship_count": sum(int(row.get("source_relationship_count", 1)) for row in rows),
                "confidence_max": max(confidences) if confidences else None,
                "confidence_avg": round(sum(confidences) / len(confidences), 4) if confidences else None,
                "descriptions": descriptions,
                "evidence": evidence,
                "raw_relationships": raw_relationships,
                "block_relationships": [
                    {
                        "block_relationship_ref": block_relationship_ref(row["block"], row["relationship_id"]),
                        "block": row["block"],
                        "source": row["source"],
                        "target": row["target"],
                        "type": row["type"],
                    }
                    for row in rows
                ],
            }
        )

    return global_relationships, dropped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-dir", type=Path, action="append", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data_ref/sanguo_chaptered/half_book_001_060_global_merge"),
    )
    parser.add_argument("--report-title", default="三國演義 001-060 Half-Book Global Merge")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    reset_output_dir(args.output, args.force)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / GENERATED_MARKER).write_text("generated\n", encoding="utf-8")

    block_dirs = args.block_dir
    block_entities = collect_block_entities(block_dirs)
    groups, merge_reasons = build_block_entity_groups(block_entities)
    global_entities, block_to_global, merge_decisions = build_global_entities(groups)
    global_relationships, dropped_relationships = build_global_relationships(block_dirs, block_to_global, global_entities)
    cross_type_candidates = find_cross_type_name_candidates(block_entities)

    block_entity_mapping = [
        {"block_entity_ref": block_ref, "unified_id": unified_id}
        for block_ref, unified_id in sorted(block_to_global.items())
    ]

    write_jsonl(args.output / "unified_entities.jsonl", global_entities)
    write_jsonl(args.output / "unified_relationships.jsonl", global_relationships)
    write_jsonl(args.output / "block_entity_to_global.jsonl", block_entity_mapping)
    write_jsonl(args.output / "merge_decisions.jsonl", merge_decisions)
    write_jsonl(args.output / "merge_reasons.jsonl", merge_reasons)
    write_jsonl(args.output / "dropped_relationships.jsonl", dropped_relationships)
    write_jsonl(args.output / "cross_type_name_candidates.jsonl", cross_type_candidates)

    raw_block_relationship_count = sum(
        len(read_jsonl(block_dir / "unified_relationships.jsonl"))
        for block_dir in block_dirs
    )
    summary = {
        "block_dirs": [block_dir.as_posix() for block_dir in block_dirs],
        "output": args.output.as_posix(),
        "block_count": len(block_dirs),
        "chapter_start": min(chapter for entity in global_entities for chapter in entity["chapters"]),
        "chapter_end": max(chapter for entity in global_entities for chapter in entity["chapters"]),
        "block_entity_count": len(block_entities),
        "global_entity_count": len(global_entities),
        "merged_entity_count_delta": len(block_entities) - len(global_entities),
        "merge_group_count": len(merge_decisions),
        "block_relationship_count": raw_block_relationship_count,
        "global_relationship_count": len(global_relationships),
        "deduped_relationship_count_delta": raw_block_relationship_count - len(global_relationships) - len(dropped_relationships),
        "dropped_relationship_count": len(dropped_relationships),
        "cross_type_name_candidate_count": len(cross_type_candidates),
    }
    (args.output / "merge_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report_lines = [
        f"# {args.report_title}",
        "",
        f"- Blocks: `{len(block_dirs)}`",
        f"- Chapters: `{summary['chapter_start']}` to `{summary['chapter_end']}`",
        f"- Block entities: `{summary['block_entity_count']}`",
        f"- Global entities: `{summary['global_entity_count']}`",
        f"- Merged entity delta: `{summary['merged_entity_count_delta']}`",
        f"- Block relationships: `{summary['block_relationship_count']}`",
        f"- Global relationships: `{summary['global_relationship_count']}`",
        f"- Deduped relationship delta: `{summary['deduped_relationship_count_delta']}`",
        f"- Dropped relationships: `{summary['dropped_relationship_count']}`",
        f"- Cross-type name candidates: `{summary['cross_type_name_candidate_count']}`",
        "",
        "## Files",
        "",
        "- `unified_entities.jsonl`",
        "- `unified_relationships.jsonl`",
        "- `block_entity_to_global.jsonl`",
        "- `merge_decisions.jsonl`",
        "- `merge_reasons.jsonl`",
        "- `cross_type_name_candidates.jsonl`",
        "- `dropped_relationships.jsonl`",
        "- `merge_summary.json`",
        "",
        "## Notes",
        "",
        "- Global merge uses block-level unified entities as the source rows.",
        "- Entity merge is still conservative and only merges within the same entity type.",
        "- Relationship dedupe groups by global source, global target, and relationship type.",
    ]
    (args.output / "README.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
