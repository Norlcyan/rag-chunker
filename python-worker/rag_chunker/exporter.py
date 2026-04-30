"""JSON export helpers for chunk results."""

from __future__ import annotations

import json
from pathlib import Path

from rag_chunker.models import Chunk, NormalizedDocument


def build_output(document: NormalizedDocument, chunks: list[Chunk]) -> dict[str, object]:
    return {
        "doc_id": document.doc_id,
        "doc_title": document.title,
        "source_type": document.source_type,
        "chunks": [chunk.to_dict() for chunk in chunks],
    }


def write_json(output: dict[str, object], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
