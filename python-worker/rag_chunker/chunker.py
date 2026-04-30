"""Structure-aware chunk generation."""

from __future__ import annotations

from rag_chunker.models import Chunk, NormalizedDocument


PREAMBLE_SECTION_TITLE = "__preamble__"


class StructureChunker:
    """Create retrieval chunks from normalized document sections."""

    def chunk(self, document: NormalizedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []

        if document.preamble.strip():
            chunks.append(
                self._build_chunk(
                    document=document,
                    index=len(chunks) + 1,
                    section_title=PREAMBLE_SECTION_TITLE,
                    section_path=[document.title, PREAMBLE_SECTION_TITLE],
                    level=0,
                    text=document.preamble,
                )
            )

        for section in document.sections:
            if not section.text.strip():
                continue
            chunks.append(
                self._build_chunk(
                    document=document,
                    index=len(chunks) + 1,
                    section_title=section.title,
                    section_path=section.path,
                    level=section.level,
                    text=section.text,
                )
            )

        return chunks

    def _build_chunk(
        self,
        document: NormalizedDocument,
        index: int,
        section_title: str,
        section_path: list[str],
        level: int,
        text: str,
    ) -> Chunk:
        retrieval_text = f"{' > '.join(section_path)}\n\n{text}"
        return Chunk(
            chunk_id=f"{document.doc_id}_chunk_{index:04d}",
            doc_id=document.doc_id,
            section_title=section_title,
            section_path=section_path,
            level=level,
            text=text,
            retrieval_text=retrieval_text,
        )
