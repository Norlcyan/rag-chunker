"""Reusable document chunking pipeline helpers."""

from __future__ import annotations

from pathlib import Path

from rag_chunker.chunker import StructureChunker
from rag_chunker.exporter import build_output
from rag_chunker.markdown_parser import MarkdownParser


MARKDOWN_SUFFIXES = {".md", ".markdown"}


def chunk_markdown_file(input_path: str | Path) -> dict[str, object]:
    """Parse a Markdown file and return the standardized Chunk JSON payload."""
    document = MarkdownParser().parse(input_path)
    chunks = StructureChunker().chunk(document)
    return build_output(document, chunks)
