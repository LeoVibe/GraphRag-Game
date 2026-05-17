#!/usr/bin/env python3
"""Embed chapter-bounded Sanguo chunks with a local Ollama embedding model."""

from __future__ import annotations

import argparse
import http.client
import json
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lancedb
import pandas as pd


GENERATED_MARKER = ".generated-by-embed_sanguo_chaptered"


@dataclass(frozen=True)
class Chunk:
    metadata: dict[str, Any]
    text: str


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def reset_output_dir(path: Path, force: bool) -> None:
    if not path.exists():
        return
    marker = path / GENERATED_MARKER
    if not force:
        raise SystemExit(f"Output already exists: {path}. Re-run with --force to replace generated files.")
    if not marker.exists():
        raise SystemExit(f"Refusing to replace {path}; generated marker is missing.")
    shutil.rmtree(path)


def load_chunks(manifest_path: Path, limit: int | None) -> list[Chunk]:
    rows = read_jsonl(manifest_path)
    if limit is not None:
        rows = rows[:limit]

    chunks: list[Chunk] = []
    for row in rows:
        chunk_file = Path(row["chunk_file"])
        chunks.append(Chunk(metadata=row, text=chunk_file.read_text(encoding="utf-8")))
    return chunks


def ollama_embed_batch(base_url: str, model: str, texts: list[str], timeout: int, retries: int) -> list[list[float]]:
    url = f"{base_url.rstrip('/')}/api/embed"
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            embeddings = data.get("embeddings")
            if not isinstance(embeddings, list) or len(embeddings) != len(texts):
                raise RuntimeError(f"Unexpected embedding response shape: {data.keys()}")
            return embeddings
        except (urllib.error.URLError, TimeoutError, RuntimeError, http.client.RemoteDisconnected) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(2**attempt)

    raise RuntimeError(f"Ollama embedding request failed after {retries + 1} attempts: {last_error}") from last_error


def batched(items: list[Chunk], size: int) -> list[list[Chunk]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def load_existing_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def write_final_outputs(output: Path, records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    df = pd.DataFrame.from_records(records)
    parquet_path = output / "embeddings.parquet"
    df.to_parquet(parquet_path, index=False)

    manifest_path = output / "embedding_manifest.jsonl"
    vector_dim = summary["vector_dim"]
    with manifest_path.open("w", encoding="utf-8") as handle:
        for record in records:
            row = {key: value for key, value in record.items() if key not in {"text", "vector"}}
            row["vector_dim"] = vector_dim
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    lancedb_dir = output / "lancedb"
    db = lancedb.connect(lancedb_dir)
    db.create_table("sanguo_chunks_embeddinggemma_300m", df, mode="overwrite")

    summary["parquet"] = parquet_path.as_posix()
    summary["lancedb_table"] = (lancedb_dir / "sanguo_chunks_embeddinggemma_300m.lance").as_posix()
    summary["embedding_manifest"] = manifest_path.as_posix()
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        "\n".join(
            [
                "# 三國演義 Chaptered Embeddings",
                "",
                f"- Model: `{summary['model']}`",
                f"- Chunks: `{summary['chunk_count']}`",
                f"- Vector dimension: `{summary['vector_dim']}`",
                f"- Batch size: `{summary['batch_size']}`",
                f"- Existing checkpoint count: `{summary['existing_checkpoint_count']}`",
                f"- Embedded this run: `{summary['embedded_this_run']}`",
                f"- Current run seconds: `{summary['current_run_seconds']}`",
                f"- Current run seconds per new chunk: `{summary['current_run_seconds_per_new_chunk']}`",
                "",
                "## Files",
                "",
                "- `embedding_records.jsonl`: incremental checkpoint with chunk metadata, text, and vector.",
                "- `embeddings.parquet`: chunk metadata, text, and vector.",
                "- `embedding_manifest.jsonl`: chunk metadata without vector payload.",
                "- `lancedb/`: LanceDB table for vector search experiments.",
                "- `summary.json`: run statistics.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data_ref/sanguo_chaptered/manifests/chunks.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data_ref/sanguo_chaptered/embeddings_embeddinggemma-300m"))
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="embeddinggemma:300m")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    if args.force and args.resume:
        raise SystemExit("--force and --resume cannot be used together")
    if args.resume:
        marker = args.output / GENERATED_MARKER
        if not marker.exists():
            raise SystemExit(f"Cannot resume; generated marker is missing: {marker}")
    else:
        reset_output_dir(args.output, args.force)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / GENERATED_MARKER).write_text("generated\n", encoding="utf-8")

    started = time.perf_counter()
    chunks = load_chunks(args.manifest, args.limit)
    if not chunks:
        raise SystemExit("No chunks found to embed.")

    records_path = args.output / "embedding_records.jsonl"
    records: list[dict[str, Any]] = load_existing_records(records_path) if args.resume else []
    existing_record_count = len(records)
    embedded_chunk_ids = {record["chunk_id"] for record in records}
    chunks = [chunk for chunk in chunks if chunk.metadata["chunk_id"] not in embedded_chunk_ids]
    target_total = existing_record_count + len(chunks)
    vector_dim: int | None = None
    if records:
        vector_dim = len(records[0]["vector"])

    for batch_index, batch in enumerate(batched(chunks, args.batch_size), start=1):
        batch_started = time.perf_counter()
        embeddings = ollama_embed_batch(
            base_url=args.base_url,
            model=args.model,
            texts=[chunk.text for chunk in batch],
            timeout=args.timeout,
            retries=args.retries,
        )
        new_records: list[dict[str, Any]] = []
        for chunk, embedding in zip(batch, embeddings, strict=True):
            if vector_dim is None:
                vector_dim = len(embedding)
            elif len(embedding) != vector_dim:
                raise RuntimeError(f"Vector dimension changed from {vector_dim} to {len(embedding)}")

            metadata = chunk.metadata
            new_records.append(
                {
                    "chunk_id": metadata["chunk_id"],
                    "global_chunk_index": metadata["global_chunk_index"],
                    "chapter_no": metadata["chapter_no"],
                    "chapter_id": metadata["chapter_id"],
                    "chapter_label": metadata["chapter_label"],
                    "chapter_title": metadata["chapter_title"],
                    "chunk_index_in_chapter": metadata["chunk_index_in_chapter"],
                    "chunk_file": metadata["chunk_file"],
                    "token_count_o200k": metadata["token_count_o200k"],
                    "char_count": metadata["char_count"],
                    "text": chunk.text,
                    "vector": embedding,
                }
            )

        with records_path.open("a", encoding="utf-8") as handle:
            for record in new_records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        records.extend(new_records)

        progress = {
            "model": args.model,
            "embedded": len(records),
            "remaining": target_total - len(records),
            "target_total": target_total,
            "vector_dim": vector_dim,
            "updated_at_unix": time.time(),
        }
        (args.output / "progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        elapsed = time.perf_counter() - batch_started
        print(
            json.dumps(
                {
                    "batch": batch_index,
                    "embedded": len(records),
                    "total": target_total,
                    "batch_seconds": round(elapsed, 3),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    total_seconds = time.perf_counter() - started
    embedded_this_run = len(records) - existing_record_count
    summary = {
        "source_manifest": args.manifest.as_posix(),
        "output": args.output.as_posix(),
        "model": args.model,
        "base_url": args.base_url,
        "chunk_count": len(records),
        "existing_checkpoint_count": existing_record_count,
        "embedded_this_run": embedded_this_run,
        "vector_dim": vector_dim,
        "batch_size": args.batch_size,
        "current_run_seconds": round(total_seconds, 3),
        "current_run_seconds_per_new_chunk": round(total_seconds / embedded_this_run, 3) if embedded_this_run else 0,
    }
    write_final_outputs(args.output, records, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
