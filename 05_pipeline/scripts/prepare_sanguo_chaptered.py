#!/usr/bin/env python3
"""Split data_ref/三國演義.md into chapter files and chapter-bounded chunks."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import tiktoken
except ImportError as exc:  # pragma: no cover - exercised by runtime environment
    raise SystemExit("Missing dependency: tiktoken. Run with graphrag-demo/.venv/bin/python.") from exc


CHAPTER_HEADING_RE = re.compile(r"^##\s+(第[一二三四五六七八九十百〇零]+回)\s+(.+?)\s*$")
GENERATED_MARKER = ".generated-by-prepare_sanguo_chaptered"


@dataclass(frozen=True)
class Chapter:
    no: int
    label: str
    title: str
    heading: str
    text: str
    start_line: int
    end_line: int


def chinese_number_to_int(value: str) -> int:
    """Parse the chapter number inside labels such as 第一百二十回."""
    value = value.removeprefix("第").removesuffix("回")
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

    if value == "十":
        return 10

    total = 0
    rest = value
    if "百" in rest:
        before, rest = rest.split("百", 1)
        total += (digits.get(before, 1) if before else 1) * 100
    if "十" in rest:
        before, rest = rest.split("十", 1)
        total += (digits.get(before, 1) if before else 1) * 10
    if rest:
        total += digits[rest]
    return total


def safe_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_chapters(source: Path) -> list[Chapter]:
    lines = source.read_text(encoding="utf-8").splitlines()
    headings: list[tuple[int, re.Match[str]]] = []
    for idx, line in enumerate(lines):
        match = CHAPTER_HEADING_RE.match(line)
        if match:
            headings.append((idx, match))

    chapters: list[Chapter] = []
    for pos, (start_idx, match) in enumerate(headings):
        end_idx = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
        label = match.group(1)
        title = match.group(2)
        no = chinese_number_to_int(label)
        body_lines = lines[start_idx + 1 : end_idx]
        text = "\n".join([f"# {label}\u3000{title}", *body_lines]).strip() + "\n"
        chapters.append(
            Chapter(
                no=no,
                label=label,
                title=title,
                heading=f"{label}\u3000{title}",
                text=text,
                start_line=start_idx + 1,
                end_line=end_idx,
            )
        )

    expected = list(range(1, len(chapters) + 1))
    actual = [chapter.no for chapter in chapters]
    if actual != expected:
        raise SystemExit(f"Chapter sequence is not continuous: {actual[:10]} ... {actual[-10:]}")

    return chapters


def reset_output_dir(path: Path, force: bool) -> None:
    if not path.exists():
        return
    marker = path / GENERATED_MARKER
    if not force:
        raise SystemExit(f"Output already exists: {path}. Re-run with --force to replace generated files.")
    if not marker.exists():
        raise SystemExit(f"Refusing to replace {path}; generated marker is missing.")
    shutil.rmtree(path)


def token_windows(token_ids: list[int], size: int, overlap: int) -> Iterable[tuple[int, int, list[int]]]:
    if overlap >= size:
        raise SystemExit("--overlap must be smaller than --chunk-size")
    start = 0
    while start < len(token_ids):
        end = min(start + size, len(token_ids))
        yield start, end, token_ids[start:end]
        if end == len(token_ids):
            break
        start = max(end - overlap, start + 1)


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data_ref/三國演義.md"))
    parser.add_argument("--output", type=Path, default=Path("data_ref/sanguo_chaptered"))
    parser.add_argument("--encoding", default="o200k_base")
    parser.add_argument("--chunk-size", type=int, default=1500)
    parser.add_argument("--overlap", type=int, default=150)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source = args.source
    output = args.output
    reset_output_dir(output, args.force)

    chapters_dir = output / "chapters_md"
    chunks_dir = output / "chunks_txt"
    manifests_dir = output / "manifests"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (output / GENERATED_MARKER).write_text("generated\n", encoding="utf-8")

    encoder = tiktoken.get_encoding(args.encoding)
    chapters = split_chapters(source)
    chapter_rows: list[dict] = []
    chunk_rows: list[dict] = []
    global_chunk_index = 0

    for chapter in chapters:
        chapter_id = f"chapter-{chapter.no:03d}"
        chapter_file = chapters_dir / f"c{chapter.no:03d}.md"
        chapter_tokens = encoder.encode(chapter.text)

        chapter_file.write_text(
            "\n".join(
                [
                    "---",
                    "book: 三國演義",
                    f"chapter_no: {chapter.no}",
                    f"chapter_id: {chapter_id}",
                    f"chapter_label: {chapter.label}",
                    f"chapter_title: {chapter.title}",
                    f"source_file: {source.as_posix()}",
                    f"source_line_start: {chapter.start_line}",
                    f"source_line_end: {chapter.end_line}",
                    f"token_count_o200k: {len(chapter_tokens)}",
                    "---",
                    "",
                    chapter.text.rstrip(),
                    "",
                ]
            ),
            encoding="utf-8",
        )

        chapter_chunk_rows: list[dict] = []
        for local_index, (token_start, token_end, window) in enumerate(
            token_windows(chapter_tokens, args.chunk_size, args.overlap), start=1
        ):
            global_chunk_index += 1
            chunk_id = f"sanguo_chaptered_c{chapter.no:03d}_k{local_index:04d}"
            chunk_file = chunks_dir / f"{chunk_id}.txt"
            chunk_text = encoder.decode(window).strip()
            chunk_text = f"# 三國演義｜{chapter.heading}｜片段 {local_index}\n\n{chunk_text}\n"
            chunk_file.write_text(chunk_text, encoding="utf-8")
            row = {
                "chunk_id": chunk_id,
                "global_chunk_index": global_chunk_index,
                "chapter_no": chapter.no,
                "chapter_id": chapter_id,
                "chapter_label": chapter.label,
                "chapter_title": chapter.title,
                "chunk_index_in_chapter": local_index,
                "chunk_file": chunk_file.as_posix(),
                "token_start": token_start,
                "token_end": token_end,
                "token_count_o200k": len(window),
                "char_count": len(chunk_text),
            }
            chunk_rows.append(row)
            chapter_chunk_rows.append(row)

        chapter_rows.append(
            {
                "chapter_no": chapter.no,
                "chapter_id": chapter_id,
                "chapter_label": chapter.label,
                "chapter_title": chapter.title,
                "chapter_file": chapter_file.as_posix(),
                "source_line_start": chapter.start_line,
                "source_line_end": chapter.end_line,
                "token_count_o200k": len(chapter_tokens),
                "char_count": len(chapter.text),
                "chunk_count": len(chapter_chunk_rows),
                "first_chunk_id": chapter_chunk_rows[0]["chunk_id"],
                "last_chunk_id": chapter_chunk_rows[-1]["chunk_id"],
            }
        )

    write_jsonl(manifests_dir / "chapters.jsonl", chapter_rows)
    write_jsonl(manifests_dir / "chunks.jsonl", chunk_rows)

    chapters_md_lines = [
        "# 三國演義章節切分清單",
        "",
        f"- 來源：`{source.as_posix()}`",
        f"- 章節數：{len(chapter_rows)}",
        f"- Chunk 數：{len(chunk_rows)}",
        f"- Chunk 設定：`{args.encoding}`, size `{args.chunk_size}`, overlap `{args.overlap}`",
        "",
        "| 回次 | 標題 | Tokens | Chunks | 檔案 |",
        "|---:|---|---:|---:|---|",
    ]
    for row in chapter_rows:
        chapters_md_lines.append(
            f"| {row['chapter_no']} | {safe_text(row['chapter_label'] + ' ' + row['chapter_title'])} | "
            f"{row['token_count_o200k']} | {row['chunk_count']} | `{row['chapter_file']}` |"
        )
    (manifests_dir / "chapters.md").write_text("\n".join(chapters_md_lines) + "\n", encoding="utf-8")

    readme = [
        "# 三國演義 Chaptered Corpus",
        "",
        "This folder is generated by `scripts/prepare_sanguo_chaptered.py`.",
        "",
        "## Outputs",
        "",
        "- `chapters_md/`: one standalone Markdown file per chapter.",
        "- `chunks_txt/`: chapter-bounded text chunks for RAG indexing.",
        "- `manifests/chapters.jsonl`: chapter metadata.",
        "- `manifests/chunks.jsonl`: chunk metadata.",
        "- `manifests/chapters.md`: human-readable chapter table.",
        "",
        "## Settings",
        "",
        f"- Source: `{source.as_posix()}`",
        f"- Chapters: `{len(chapter_rows)}`",
        f"- Chunks: `{len(chunk_rows)}`",
        f"- Encoding: `{args.encoding}`",
        f"- Chunk size: `{args.chunk_size}`",
        f"- Overlap: `{args.overlap}`",
        "",
        "The chunk files never cross chapter boundaries. Use the manifests to recover chapter metadata during retrieval experiments.",
        "",
    ]
    (output / "README.md").write_text("\n".join(readme), encoding="utf-8")

    summary = {
        "source": source.as_posix(),
        "output": output.as_posix(),
        "chapter_count": len(chapter_rows),
        "chunk_count": len(chunk_rows),
        "encoding": args.encoding,
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "min_chapter_tokens": min(row["token_count_o200k"] for row in chapter_rows),
        "max_chapter_tokens": max(row["token_count_o200k"] for row in chapter_rows),
        "min_chunks_per_chapter": min(row["chunk_count"] for row in chapter_rows),
        "max_chunks_per_chapter": max(row["chunk_count"] for row in chapter_rows),
    }
    (manifests_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
