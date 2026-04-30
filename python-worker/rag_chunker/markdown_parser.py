"""Markdown parser for the first structure-aware chunking MVP."""

from __future__ import annotations

import re
from pathlib import Path

from rag_chunker.models import NormalizedDocument, Section


HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE_PATTERN = re.compile(r"^[ \t]*(```+|~~~+)")


class MarkdownParser:
    """Parse Markdown headings into a normalized document model."""

    def __init__(self, max_section_level: int = 3) -> None:
        self.max_section_level = max_section_level

    def parse(self, input_path: str | Path) -> NormalizedDocument:
        path = Path(input_path)
        text = path.read_text(encoding="utf-8-sig")
        return self.parse_text(text, doc_id=path.stem)

    def parse_text(self, text: str, doc_id: str) -> NormalizedDocument:
        text = text.lstrip("\ufeff")
        lines = text.splitlines()
        doc_title = doc_id
        heading_stack: dict[int, str] = {}
        preamble_lines: list[str] = []
        sections: list[Section] = []
        current: _SectionBuilder | None = None
        in_fence = False

        for line_number, line in enumerate(lines, start=1):
            fence = FENCE_PATTERN.match(line)
            if fence:
                in_fence = not in_fence
                self._append_content(current, preamble_lines, line)
                continue

            heading = None if in_fence else HEADING_PATTERN.match(line)
            if heading is None:
                self._append_content(current, preamble_lines, line)
                continue

            level = len(heading.group(1))
            title = heading.group(2).strip()

            if level == 1:
                if doc_title == doc_id:
                    doc_title = title
                heading_stack = {1: doc_title}
                if current is None:
                    continue
                current.lines.append(line)
                continue

            if level > self.max_section_level:
                self._append_content(current, preamble_lines, line)
                continue

            if current is not None:
                sections.append(current.build(line_number - 1))

            heading_stack = self._update_heading_stack(heading_stack, level, title, doc_title)
            current = _SectionBuilder(
                title=title,
                level=level,
                path=self._build_path(heading_stack, doc_title, level),
                line_start=line_number,
            )

        if current is not None:
            sections.append(current.build(len(lines)))

        return NormalizedDocument(
            doc_id=doc_id,
            title=doc_title,
            source_type="markdown",
            preamble=self._normalize_block(preamble_lines),
            sections=sections,
        )

    def _append_content(
        self,
        current: "_SectionBuilder | None",
        preamble_lines: list[str],
        line: str,
    ) -> None:
        if current is None:
            preamble_lines.append(line)
        else:
            current.lines.append(line)

    def _update_heading_stack(
        self,
        heading_stack: dict[int, str],
        level: int,
        title: str,
        doc_title: str,
    ) -> dict[int, str]:
        next_stack = {1: heading_stack.get(1, doc_title)}
        for current_level in range(2, level):
            if current_level in heading_stack:
                next_stack[current_level] = heading_stack[current_level]
        next_stack[level] = title
        return next_stack

    def _build_path(
        self,
        heading_stack: dict[int, str],
        doc_title: str,
        level: int,
    ) -> list[str]:
        path = [heading_stack.get(1, doc_title)]
        for current_level in range(2, level + 1):
            title = heading_stack.get(current_level)
            if title:
                path.append(title)
        return path

    def _normalize_block(self, lines: list[str]) -> str:
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)


class _SectionBuilder:
    def __init__(self, title: str, level: int, path: list[str], line_start: int) -> None:
        self.title = title
        self.level = level
        self.path = path
        self.line_start = line_start
        self.lines: list[str] = []

    def build(self, line_end: int) -> Section:
        return Section(
            title=self.title,
            level=self.level,
            path=self.path,
            text=self._normalize_text(),
            line_start=self.line_start,
            line_end=line_end,
        )

    def _normalize_text(self) -> str:
        lines = list(self.lines)
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)
