from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from rag_chunker.chunker import PREAMBLE_SECTION_TITLE, StructureChunker
from rag_chunker.cli import main
from rag_chunker.exporter import build_output
from rag_chunker.markdown_parser import MarkdownParser


class MarkdownParserTest(unittest.TestCase):
    def test_parse_title_preamble_sections_and_code_fence(self) -> None:
        markdown = "\ufeff# 文档标题\n\n导语内容\n\n## 第一节\n正文 A\n\n```text\n## 不是标题\n```\n\n### 子节\n正文 B\n"

        document = MarkdownParser().parse_text(markdown, doc_id="demo")

        self.assertEqual(document.title, "文档标题")
        self.assertEqual(document.preamble, "导语内容")
        self.assertEqual(len(document.sections), 2)
        self.assertEqual(document.sections[0].title, "第一节")
        self.assertIn("## 不是标题", document.sections[0].text)
        self.assertEqual(document.sections[1].path, ["文档标题", "第一节", "子节"])

    def test_deep_headings_are_preserved_in_current_section_text(self) -> None:
        markdown = "# 文档标题\n\n## 第一节\n正文 A\n\n#### 深层标题\n正文 B\n"

        document = MarkdownParser().parse_text(markdown, doc_id="demo")

        self.assertEqual(len(document.sections), 1)
        self.assertIn("#### 深层标题", document.sections[0].text)


class StructureChunkerTest(unittest.TestCase):
    def test_chunk_output_contains_preamble_and_retrieval_context(self) -> None:
        markdown = "# 文档标题\n\n导语内容\n\n## 第一节\n正文 A\n\n### 子节\n正文 B\n"
        document = MarkdownParser().parse_text(markdown, doc_id="demo")

        chunks = StructureChunker().chunk(document)
        output = build_output(document, chunks)

        self.assertEqual(output["doc_id"], "demo")
        self.assertEqual(output["doc_title"], "文档标题")
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].section_title, PREAMBLE_SECTION_TITLE)
        self.assertEqual(chunks[0].level, 0)
        self.assertEqual(chunks[0].section_path, ["文档标题", PREAMBLE_SECTION_TITLE])
        self.assertTrue(chunks[1].retrieval_text.startswith("文档标题 > 第一节\n\n"))
        self.assertTrue(chunks[2].retrieval_text.startswith("文档标题 > 第一节 > 子节\n\n"))


class CliTest(unittest.TestCase):
    def test_cli_writes_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            base = Path(temporary_dir)
            input_path = base / "demo.md"
            output_path = base / "nested" / "chunks.json"
            input_path.write_text("# 文档标题\n\n## 第一节\n正文 A\n", encoding="utf-8")

            exit_code = main([str(input_path), "--out", str(output_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["doc_id"], "demo")
            self.assertEqual(payload["doc_title"], "文档标题")
            self.assertEqual(payload["source_type"], "markdown")
            self.assertEqual(len(payload["chunks"]), 1)

    def test_cli_rejects_non_markdown_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            input_path = Path(temporary_dir) / "demo.txt"
            input_path.write_text("text", encoding="utf-8")

            with redirect_stderr(StringIO()):
                exit_code = main([str(input_path)])

            self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
