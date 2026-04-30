"""Command line entrypoint for the Python chunking worker."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from rag_chunker.chunker import StructureChunker
from rag_chunker.exporter import build_output, write_json
from rag_chunker.markdown_parser import MarkdownParser


MARKDOWN_SUFFIXES = {".md", ".markdown"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chunk a Markdown document into JSON.")
    parser.add_argument("input", help="Path to the input Markdown document.")
    parser.add_argument("--out", help="Path to write the output JSON. Defaults to stdout.")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file does not exist: {input_path}", file=sys.stderr)
        return 2
    if not input_path.is_file():
        print(f"Input path is not a file: {input_path}", file=sys.stderr)
        return 2
    if input_path.suffix.lower() not in MARKDOWN_SUFFIXES:
        print(f"Unsupported input type: {input_path.suffix or '<none>'}", file=sys.stderr)
        return 2

    try:
        document = MarkdownParser().parse(input_path)
        chunks = StructureChunker().chunk(document)
        output = build_output(document, chunks)
        if args.out:
            write_json(output, args.out)
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
    except OSError as exc:
        print(f"Failed to chunk document: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
