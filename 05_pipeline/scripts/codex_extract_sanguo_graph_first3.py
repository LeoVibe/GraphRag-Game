#!/usr/bin/env python3
"""Use Codex CLI to extract per-chapter graph JSON for Sanguo chapters."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any


SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["book", "chapter_no", "chapter_title", "model", "entities", "relationships", "events", "notes"],
    "properties": {
        "book": {"type": "string"},
        "chapter_no": {"type": "integer"},
        "chapter_title": {"type": "string"},
        "model": {"type": "string"},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "type", "aliases", "description", "evidence"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["character", "faction", "location", "battle", "event", "title", "object", "strategy", "army"],
                    },
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "target", "type", "description", "evidence", "confidence"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "name", "summary", "participants", "locations", "evidence"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "summary": {"type": "string"},
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "locations": {"type": "array", "items": {"type": "string"}},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
}


def chapter_prompt(chapter_file: Path, chapter_no: int, model: str) -> str:
    return f"""
你要為《三國演義》的章節建立知識圖抽取結果。

請讀取這個檔案：
{chapter_file.as_posix()}

任務：
1. 抽取本章出現的重要人物、勢力、地點、戰役、事件、官職/稱號、物件、策略、軍隊。
2. 抽取它們之間的關係，例如結義、統領、攻打、救援、隸屬、任命、敵對、贈與、行軍、計策、事件參與。
3. 請保留原文繁體中文名稱；別名可放在 aliases，例如「劉備 / 玄德」。
4. evidence 請用非常短的原文片段或改寫摘要，不要長篇引用。
5. 不要臆測正文沒有支持的關係。
6. 輸出必須完全符合 JSON schema；不要 Markdown、不要解釋文字。

固定欄位：
- book: 三國演義
- chapter_no: {chapter_no}
- model: {model}
""".strip()


def validate_graph(data: dict[str, Any]) -> None:
    entity_ids = {entity["id"] for entity in data["entities"]}
    for rel in data["relationships"]:
        if rel["source"] not in entity_ids:
            raise ValueError(f"Relationship source is not an entity id: {rel['source']}")
        if rel["target"] not in entity_ids:
            raise ValueError(f"Relationship target is not an entity id: {rel['target']}")


def graph_score(data: dict[str, Any]) -> int:
    return len(data.get("entities", [])) + len(data.get("relationships", [])) + len(data.get("events", []))


def graph_candidates_from_text(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{") or not stripped.endswith("}"):
            continue
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if {"book", "chapter_no", "chapter_title", "entities", "relationships", "events"}.issubset(data):
            try:
                validate_graph(data)
            except Exception:
                continue
            candidates.append(data)
    return candidates


def best_graph_candidate(paths: list[Path]) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            data = json.loads(text)
            validate_graph(data)
            candidates.append(data)
        except Exception:
            candidates.extend(graph_candidates_from_text(text))
    if not candidates:
        return None
    return max(candidates, key=graph_score)


def run_codex(prompt: str, cwd: Path, schema_path: Path, output_last_message: Path, model: str, timeout: int) -> subprocess.CompletedProcess[str]:
    command = [
        "codex",
        "-m",
        model,
        "-C",
        cwd.as_posix(),
        "-s",
        "workspace-write",
        "-a",
        "never",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--color",
        "never",
        "--output-schema",
        schema_path.as_posix(),
        "--output-last-message",
        output_last_message.as_posix(),
        "-",
    ]
    return subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def load_existing_summary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_run_files(output: Path, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    (output / "run_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    completed = [row for row in rows if row.get("returncode") == 0 and row.get("entity_count") is not None]
    failed = [row for row in rows if row.get("returncode") not in (None, 0) or row.get("error")]
    progress = {
        "model": args.model,
        "start_chapter": args.start_chapter,
        "end_chapter": args.end_chapter,
        "target_chapter_count": args.end_chapter - args.start_chapter + 1,
        "completed_chapter_count": len(completed),
        "failed_chapter_count": len(failed),
        "completed_chapters": [row["chapter_no"] for row in completed],
        "failed_chapters": [row["chapter_no"] for row in failed],
        "updated_at_unix": time.time(),
    }
    (output / "progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "\n".join(
            [
                "# 三國演義 Codex CLI Graph Extract",
                "",
                f"- Model: `{args.model}`",
                f"- Chapters: `{args.start_chapter}` to `{args.end_chapter}`",
                f"- Completed: `{len(completed)}` / `{progress['target_chapter_count']}`",
                f"- Failed: `{len(failed)}`",
                "- Output JSON pattern: `cNNN_graph.json`",
                "- Schema: `graph_extract.schema.json`",
                "- Run summary: `run_summary.json`",
                "- Progress: `progress.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters-dir", type=Path, default=Path("data_ref/sanguo_chaptered/chapters_md"))
    parser.add_argument("--output", type=Path, default=Path("data_ref/sanguo_chaptered/graph_extract_codex_gpt-5.5"))
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--start-chapter", type=int, default=1)
    parser.add_argument("--end-chapter", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    schema_path = args.output / "graph_extract.schema.json"
    schema_path.write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_path = args.output / "run_summary.json"
    run_rows: list[dict[str, Any]] = load_existing_summary(summary_path) if args.resume else []
    completed_chapters = {
        row["chapter_no"]
        for row in run_rows
        if row.get("returncode") == 0 and row.get("entity_count", 0) > 0 and Path(row["final_json"]).exists()
    }
    for chapter_no in range(args.start_chapter, args.end_chapter + 1):
        chapter_file = args.chapters_dir / f"c{chapter_no:03d}.md"
        if not chapter_file.exists():
            raise SystemExit(f"Missing chapter file: {chapter_file}")

        output_last_message = args.output / f"c{chapter_no:03d}.last_message.json"
        stdout_log = args.output / f"c{chapter_no:03d}.stdout.log"
        stderr_log = args.output / f"c{chapter_no:03d}.stderr.log"
        final_json = args.output / f"c{chapter_no:03d}_graph.json"

        if args.resume and chapter_no in completed_chapters:
            print(
                json.dumps(
                    {
                        "chapter_no": chapter_no,
                        "status": "skipped_existing",
                        "final_json": final_json.as_posix(),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            continue

        started = time.perf_counter()
        try:
            result = run_codex(
                prompt=chapter_prompt(chapter_file, chapter_no, args.model),
                cwd=Path.cwd(),
                schema_path=schema_path,
                output_last_message=output_last_message,
                model=args.model,
                timeout=args.timeout,
            )
            returncode = result.returncode
            stdout_log.write_text(result.stdout, encoding="utf-8")
            stderr_log.write_text(result.stderr, encoding="utf-8")
        except subprocess.TimeoutExpired as exc:
            returncode = 124
            stdout_log.write_text(exc.stdout or "", encoding="utf-8")
            stderr_log.write_text(exc.stderr or f"Timeout after {args.timeout} seconds", encoding="utf-8")
        elapsed = time.perf_counter() - started

        row = {
            "chapter_no": chapter_no,
            "chapter_file": chapter_file.as_posix(),
            "returncode": returncode,
            "seconds": round(elapsed, 3),
            "stdout_log": stdout_log.as_posix(),
            "stderr_log": stderr_log.as_posix(),
            "output_last_message": output_last_message.as_posix(),
            "final_json": final_json.as_posix(),
        }
        try:
            if returncode == 0:
                data = best_graph_candidate([output_last_message, stdout_log, stderr_log])
                if data is None:
                    raise ValueError("no_valid_graph_json_found")
                final_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                row["entity_count"] = len(data["entities"])
                row["relationship_count"] = len(data["relationships"])
                row["event_count"] = len(data["events"])
            elif returncode != 0:
                row["error"] = f"codex_returncode_{returncode}"
            else:
                row["error"] = "missing_output_last_message"
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"

        run_rows = [existing for existing in run_rows if existing["chapter_no"] != chapter_no]
        run_rows.append(row)
        run_rows.sort(key=lambda existing: existing["chapter_no"])
        write_run_files(args.output, run_rows, args)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        if row.get("error") and not args.continue_on_error:
            raise SystemExit(f"Chapter {chapter_no} failed: {row['error']}")

    write_run_files(args.output, run_rows, args)


if __name__ == "__main__":
    main()
