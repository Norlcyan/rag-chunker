"""Core data models for normalized documents and chunks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    """A normalized document section identified by a structural heading."""

    title: str
    level: int
    path: list[str]
    text: str
    line_start: int
    line_end: int


@dataclass(frozen=True)
class NormalizedDocument:
    """Parser output shared by chunkers and exporters."""

    doc_id: str
    title: str
    source_type: str
    preamble: str = ""
    sections: list[Section] = field(default_factory=list)


@dataclass(frozen=True)
class Chunk:
    """A retrieval-ready text chunk with structural context."""

    chunk_id: str
    doc_id: str
    section_title: str
    section_path: list[str]
    level: int
    text: str
    retrieval_text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "level": self.level,
            "text": self.text,
            "retrieval_text": self.retrieval_text,
        }
