"""StructureChunker / Exporter / CLI 边界情况测试."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from rag_chunker.chunker import PREAMBLE_SECTION_TITLE, StructureChunker
from rag_chunker.cli import main
from rag_chunker.exporter import build_output, write_json
from rag_chunker.markdown_parser import MarkdownParser


# ── helpers ──────────────────────────────────────────────────────────────

def _parse(chunk: str, doc_id: str = "test") -> tuple:
    """快捷方式：解析 markdown 文本并分块."""
    document = MarkdownParser().parse_text(chunk, doc_id=doc_id)
    chunks = StructureChunker().chunk(document)
    return document, chunks


# ── StructureChunker ─────────────────────────────────────────────────────

class StructureChunkerEdgeTest(unittest.TestCase):
    """分块器边界行为."""

    def test_only_preamble_no_sections(self) -> None:
        """仅导语无章节 → 应仅产生一个 preamble 块."""
        _, chunks = _parse("只有导语内容。\n")

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].section_title, PREAMBLE_SECTION_TITLE)
        self.assertEqual(chunks[0].level, 0)
        self.assertEqual(chunks[0].chunk_id, "test_chunk_0001")

    def test_no_preamble_sections_only(self) -> None:
        """无导语但有章节 → 不应产生 preamble 块，索引仍从 1 开始."""
        markdown = "# 文档\n\n## 第一节\n正文A\n\n## 第二节\n正文B\n"
        _, chunks = _parse(markdown)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].section_title, "第一节")
        self.assertEqual(chunks[0].chunk_id, "test_chunk_0001")
        self.assertEqual(chunks[1].section_title, "第二节")
        self.assertEqual(chunks[1].chunk_id, "test_chunk_0002")

    def test_whitespace_only_section_is_skipped(self) -> None:
        """仅含空白的章节应被跳过."""
        markdown = "# 文档\n\n## 第一节\n正文\n\n## 第二节\n   \n\n## 第三节\n正文C\n"
        _, chunks = _parse(markdown)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].section_title, "第一节")
        self.assertEqual(chunks[1].section_title, "第三节")

    def test_preamble_whitespace_only_is_skipped(self) -> None:
        """仅含空白的导语不应产生 preamble 块."""
        _, chunks = _parse("   \n\n\n")

        self.assertEqual(len(chunks), 0)

    def test_chunk_index_without_preamble(self) -> None:
        """无导语时 chunk 索引从 0001 开始且连续."""
        markdown = "# 文档\n\n## A\nA\n\n## B\nB\n\n## C\nC\n"
        _, chunks = _parse(markdown)

        ids = [c.chunk_id for c in chunks]
        self.assertEqual(ids, ["test_chunk_0001", "test_chunk_0002", "test_chunk_0003"])


# ── Exporter ─────────────────────────────────────────────────────────────

class ExporterTest(unittest.TestCase):
    """导出器单元测试."""

    def test_build_output_structure(self) -> None:
        """验证 build_output 返回的 JSON 结构."""
        document, chunks = _parse("# 文档\n\n## A\n正文\n")
        output = build_output(document, chunks)

        self.assertEqual(output["doc_id"], "test")
        self.assertEqual(output["doc_title"], "文档")
        self.assertEqual(output["source_type"], "markdown")
        self.assertIsInstance(output["chunks"], list)
        self.assertEqual(len(output["chunks"]), 1)
        chunk_dict = output["chunks"][0]
        self.assertIn("chunk_id", chunk_dict)
        self.assertIn("retrieval_text", chunk_dict)
        self.assertIn("section_path", chunk_dict)

    def test_write_json_creates_nested_directory(self) -> None:
        """write_json 应自动创建嵌套目录."""
        document, chunks = _parse("# 文档\n\n## A\n正文\n")
        output = build_output(document, chunks)

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "a" / "b" / "c" / "out.json"
            write_json(output, out_path)

            self.assertTrue(out_path.exists())
            payload = json.loads(out_path.read_text("utf-8"))
            self.assertEqual(payload["doc_id"], "test")


# ── CLI ──────────────────────────────────────────────────────────────────

class CliEdgeTest(unittest.TestCase):
    """CLI 边界行为."""

    def test_stdout_mode_no_out_arg(self) -> None:
        """不带 --out 时输出到 stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "doc.md"
            input_path.write_text("# 文档\n\n## A\n正文\n", encoding="utf-8")

            buf = StringIO()
            with redirect_stdout(buf):
                exit_code = main([str(input_path)])

            self.assertEqual(exit_code, 0)
            result = json.loads(buf.getvalue())
            self.assertEqual(result["doc_id"], "doc")

    def test_file_not_found(self) -> None:
        """输入文件不存在应返回退出码 2."""
        with redirect_stderr(StringIO()):
            exit_code = main(["/nonexistent/path.md"])
        self.assertEqual(exit_code, 2)

    def test_directory_instead_of_file(self) -> None:
        """输入路径是目录而非文件应返回退出码 2."""
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stderr(StringIO()):
                exit_code = main([tmp])
            self.assertEqual(exit_code, 2)

    def test_markdown_extension_accepted(self) -> None:
        """.markdown 扩展名应被接受."""
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "doc.markdown"
            input_path.write_text("# 文档\n\n## A\n正文\n", encoding="utf-8")

            with redirect_stdout(StringIO()):
                exit_code = main([str(input_path)])

            self.assertEqual(exit_code, 0)

    def test_no_extension_is_rejected(self) -> None:
        """无扩展名的文件应被拒绝."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "noext"
            p.write_text("# doc\n", encoding="utf-8")
            with redirect_stderr(StringIO()):
                exit_code = main([str(p)])
            self.assertEqual(exit_code, 2)

    def test_cli_with_bom_handling(self) -> None:
        """端到端：带 BOM 的 UTF-8 文件能正确处理并输出 JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "bom.md"
            output_path = Path(tmp) / "out.json"
            # 写入带 BOM 的文件
            input_path.write_text("\ufeff# 标题\n\n## 章节\n内容\n", encoding="utf-8-sig")

            exit_code = main([str(input_path), "--out", str(output_path)])
            self.assertEqual(exit_code, 0)

            payload = json.loads(output_path.read_text("utf-8"))
            self.assertEqual(payload["doc_title"], "标题")
            self.assertNotIn("\ufeff", payload["doc_title"])


class FullPipelineTest(unittest.TestCase):
    """完整流水线端到端测试."""

    def test_roundtrip_empty_document(self) -> None:
        """空文档的流水线输出."""
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "empty.md"
            output_path = Path(tmp) / "out.json"
            input_path.write_text("", encoding="utf-8")

            exit_code = main([str(input_path), "--out", str(output_path)])
            self.assertEqual(exit_code, 0)

            payload = json.loads(output_path.read_text("utf-8"))
            self.assertEqual(payload["doc_id"], "empty")
            self.assertEqual(payload["chunks"], [])

    def test_roundtrip_with_max_section_level_stress(self) -> None:
        """6 级标题 + 代码围栏 + 空章节混合的端到端测试."""
        markdown = (
            "\ufeff# 项目文档\n\n"
            "项目导语第一行。\n"
            "项目导语第二行。\n\n"
            "## 概述\n\n"
            "概述内容。\n\n"
            "### 背景\n\n"
            "```python\n"
            "# 这是代码注释不是标题\n"
            "def foo():\n"
            "    pass\n"
            "```\n\n"
            "背景更多内容。\n\n"
            "### 目标\n\n"
            "目标内容。\n\n"
            "## 详细设计\n\n"
            "设计内容第一段。\n\n"
            "~~~\n"
            "## 围栏内的标题\n"
            "~~~\n\n"
            "设计内容第二段。\n\n"
            "### 架构\n\n"
            "架构描述。\n\n"
            "#### 模块 A\n\n"
            "模块 A 内容。\n\n"
            "#### 模块 B\n\n"
            "模块 B 内容。\n\n"
            "### 接口\n\n"
            "接口描述。\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "stress.md"
            output_path = Path(tmp) / "out.json"
            input_path.write_text(markdown, encoding="utf-8-sig")

            exit_code = main([str(input_path), "--out", str(output_path)])
            self.assertEqual(exit_code, 0)

            payload = json.loads(output_path.read_text("utf-8"))
            self.assertEqual(payload["doc_id"], "stress")
            self.assertEqual(payload["doc_title"], "项目文档")
            self.assertEqual(payload["source_type"], "markdown")

            chunks = payload["chunks"]
            # 导语 + 概述 + 背景 + 目标 + 详细设计 + 架构 + 接口 = 7
            # 但模块 A/B (####) 默认被合入父 section "架构"，不会独立成 chunk
            self.assertGreaterEqual(len(chunks), 5)

            # 导语 chunk
            self.assertEqual(chunks[0]["section_title"], PREAMBLE_SECTION_TITLE)
            self.assertIn("项目导语第一行。", chunks[0]["text"])

            # 代码围栏内的 # 注释不应被解析为标题
            bg_chunks = [c for c in chunks if c["section_title"] == "背景"]
            self.assertEqual(len(bg_chunks), 1)
            self.assertIn("# 这是代码注释不是标题", bg_chunks[0]["text"])

            # 围栏（~~~）内的 ## 不应被解析为标题
            design_chunks = [c for c in chunks if c["section_title"] == "详细设计"]
            self.assertEqual(len(design_chunks), 1)
            self.assertIn("## 围栏内的标题", design_chunks[0]["text"])

            # retrieval_text 格式
            for chunk in chunks:
                self.assertIn(chunk["section_title"], chunk["retrieval_text"])
                self.assertIn(chunk["text"], chunk["retrieval_text"])


if __name__ == "__main__":
    unittest.main()
