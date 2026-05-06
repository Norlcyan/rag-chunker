"""Batch command line entrypoint for sample Markdown chunking."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, TextIO

from rag_chunker.exporter import write_json
from rag_chunker.pipeline import MARKDOWN_SUFFIXES, chunk_markdown_file


@dataclass(frozen=True)
class BatchSummary:
    """Final batch execution counters."""

    success_count: int
    failure_count: int
    output_dir: Path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chunk Markdown files in a directory into JSON.")
    parser.add_argument("input_dir", help="Directory containing Markdown documents.")
    parser.add_argument("--out-dir", required=True, help="Directory to write output JSON files.")
    args = parser.parse_args(argv)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.out_dir)

    if not input_dir.exists():
        print(f"Input directory does not exist: {input_dir}", file=sys.stderr)
        return 2
    if not input_dir.is_dir():
        print(f"Input path is not a directory: {input_dir}", file=sys.stderr)
        return 2

    summary = run_batch(input_dir=input_dir, output_dir=output_dir, stdout=sys.stdout)
    return 1 if summary.failure_count else 0


def run_batch(input_dir: Path, output_dir: Path, stdout: TextIO) -> BatchSummary:
    """Run chunking for all supported Markdown files without stopping on file errors."""
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failure_count = 0
    for input_path in iter_markdown_files(input_dir):
        output_path = build_output_path(input_path, input_dir, output_dir)
        try:
            payload = chunk_markdown_file(input_path)
            write_json(payload, output_path)
        except Exception as exc:
            failure_count += 1
            print(f"FAIL {_display_path(input_path)}  →  {exc}", file=stdout)
            continue

        success_count += 1
        print(f"OK  {_display_path(input_path)}  →  {_display_path(output_path)}", file=stdout)

    print("---", file=stdout)
    print(
        f"成功: {success_count}  失败: {failure_count}  输出目录: {_display_path(output_dir)}",
        file=stdout,
    )
    return BatchSummary(success_count=success_count, failure_count=failure_count, output_dir=output_dir)


def iter_markdown_files(input_dir: Path) -> list[Path]:
    """Return supported Markdown files in stable path order."""
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in MARKDOWN_SUFFIXES
    )


def build_output_path(input_path: Path, input_dir: Path, output_dir: Path) -> Path:
    relative_path = input_path.relative_to(input_dir).with_suffix(".json")
    return output_dir / input_dir.name / relative_path


def _display_path(path: Path) -> str:
    return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
