"""MarkdownParser 边界情况测试."""

from __future__ import annotations

import unittest

from rag_chunker.markdown_parser import MarkdownParser


class EmptyOrMinimalDocumentTest(unittest.TestCase):
    """空文档 / 极简文档的解析行为."""

    def test_empty_document(self) -> None:
        """空文档：preamble 为空，无 sections."""
        document = MarkdownParser().parse_text("", doc_id="empty")

        self.assertEqual(document.doc_id, "empty")
        self.assertEqual(document.title, "empty")
        self.assertEqual(document.preamble, "")
        self.assertEqual(len(document.sections), 0)

    def test_only_preamble_no_headings(self) -> None:
        """没有任何标题的文档：全部内容进入 preamble."""
        document = MarkdownParser().parse_text(
            "这是一段导语。\n\n第二行。\n", doc_id="only_preamble"
        )

        self.assertEqual(document.title, "only_preamble")
        self.assertEqual(document.preamble, "这是一段导语。\n\n第二行。")
        self.assertEqual(len(document.sections), 0)

    def test_only_h1_without_sub_headings(self) -> None:
        """仅有 h1 没有 h2/h3 的文档."""
        document = MarkdownParser().parse_text(
            "# 唯一标题\n\n一些正文内容。\n", doc_id="only_h1"
        )

        self.assertEqual(document.title, "唯一标题")
        self.assertIn("一些正文内容。", document.preamble)
        # h1 不产生 section
        self.assertEqual(len(document.sections), 0)

    def test_preamble_followed_by_h1_only(self) -> None:
        """导语后只有一个 h1，没有子标题；h1 后的内容继续归入 preamble."""
        document = MarkdownParser().parse_text(
            "导语行。\n\n# 文档名\n\n正文。\n", doc_id="preamble_h1"
        )

        self.assertEqual(document.title, "文档名")
        # h1 本身不产生 section，其后的正文因为无 section 承接，仍进入 preamble
        self.assertIn("导语行。", document.preamble)
        self.assertIn("正文。", document.preamble)
        self.assertEqual(len(document.sections), 0)


class FenceVariantTest(unittest.TestCase):
    """围栏变体测试."""

    def test_tilde_fence_blocks_are_respected(self) -> None:
        """~~~ 围栏内的 # 不应被识别为标题."""
        markdown = "# 文档\n\n## 第一节\n正文\n\n~~~\n# 不是标题\n~~~\n"
        document = MarkdownParser().parse_text(markdown, doc_id="tilde")

        self.assertEqual(len(document.sections), 1)
        self.assertEqual(document.sections[0].title, "第一节")
        self.assertIn("# 不是标题", document.sections[0].text)


class HeadingFormatTest(unittest.TestCase):
    """标题格式变体测试."""

    def test_trailing_hash_in_heading_is_stripped(self) -> None:
        """尾随 # 应从标题文本中去除."""
        markdown = "# 文档\n\n## 标题带尾随 ##\n正文\n\n### 另一个 ####\n正文2\n"
        document = MarkdownParser().parse_text(markdown, doc_id="trailing")

        self.assertEqual(document.sections[0].title, "标题带尾随")
        self.assertEqual(document.sections[1].title, "另一个")

    def test_heading_with_extra_whitespace(self) -> None:
        """标题前后的多余空白应被正确处理."""
        markdown = "# 文档\n\n##   标题前后有空格   \n正文\n"
        document = MarkdownParser().parse_text(markdown, doc_id="whitespace")

        self.assertEqual(document.sections[0].title, "标题前后有空格")


class MaxSectionLevelTest(unittest.TestCase):
    """max_section_level 配置测试."""

    def test_max_level_1_only_h1_creates_no_sections(self) -> None:
        """max_section_level=1 时，h1 不产生 section."""
        parser = MarkdownParser(max_section_level=1)
        document = parser.parse_text("# 文档\n\n正文。\n", doc_id="max1")

        self.assertEqual(len(document.sections), 0)

    def test_max_level_2_h3_becomes_content(self) -> None:
        """max_section_level=2 时，h3 被当作正文保留在父 section 中."""
        parser = MarkdownParser(max_section_level=2)
        markdown = "# 文档\n\n## 第一节\n正文\n\n### 三级标题\n更多正文\n"
        document = parser.parse_text(markdown, doc_id="max2")

        self.assertEqual(len(document.sections), 1)
        self.assertEqual(document.sections[0].title, "第一节")
        self.assertIn("### 三级标题", document.sections[0].text)

    def test_max_level_6_all_headings_create_sections(self) -> None:
        """max_section_level=6 时，h1-h6 都产生 section."""
        parser = MarkdownParser(max_section_level=6)
        markdown = (
            "# 文档\n\n"
            "## 第一节\n正文\n\n"
            "### 子节\n正文\n\n"
            "#### 四级\n正文\n\n"
            "##### 五级\n正文\n\n"
            "###### 六级\n正文\n"
        )
        document = parser.parse_text(markdown, doc_id="max6")

        self.assertEqual(len(document.sections), 5)
        self.assertEqual(document.sections[0].level, 2)
        self.assertEqual(document.sections[4].level, 6)
        self.assertEqual(document.sections[4].title, "六级")


class SectionPathTest(unittest.TestCase):
    """章节路径构建测试."""

    def test_path_with_skipped_level(self) -> None:
        """h2 后直接出现 h4（跳过了 h3），h4 的路径应正确."""
        markdown = "# 文档\n\n## 第一节\n正文\n\n#### 四级标题\n正文\n"
        document = MarkdownParser().parse_text(markdown, doc_id="skip_level")

        self.assertEqual(len(document.sections), 1)
        # 四级超出 max_section_level=3，留在 text 中
        self.assertIn("#### 四级标题", document.sections[0].text)

    def test_path_with_skipped_level_max6(self) -> None:
        """max_section_level=6 时，跳级路径应只包含存在的祖先."""
        parser = MarkdownParser(max_section_level=6)
        markdown = "# 文档\n\n## 第一节\n正文\n\n#### 四级（跳过三级）\n正文\n"
        document = parser.parse_text(markdown, doc_id="skip6")

        self.assertEqual(len(document.sections), 2)
        self.assertEqual(document.sections[1].level, 4)
        self.assertEqual(document.sections[1].path, ["文档", "第一节", "四级（跳过三级）"])

    def test_multiple_h2_sections(self) -> None:
        """多个同级 h2 section 各自独立."""
        markdown = "# 文档\n\n## 第一节\n正文A\n\n## 第二节\n正文B\n\n## 第三节\n正文C\n"
        document = MarkdownParser().parse_text(markdown, doc_id="multi_h2")

        self.assertEqual(len(document.sections), 3)
        self.assertEqual(document.sections[0].title, "第一节")
        self.assertEqual(document.sections[1].title, "第二节")
        self.assertEqual(document.sections[2].title, "第三节")
        self.assertEqual(document.sections[0].path, ["文档", "第一节"])
        self.assertEqual(document.sections[2].path, ["文档", "第三节"])

    def test_nested_h3_under_correct_parent(self) -> None:
        """h3 应归属到最近的上层 h2."""
        markdown = (
            "# 文档\n\n"
            "## 第一节\n正文A\n\n"
            "### 子节1\n正文B\n\n"
            "## 第二节\n正文C\n\n"
            "### 子节2\n正文D\n"
        )
        document = MarkdownParser().parse_text(markdown, doc_id="nested")

        self.assertEqual(len(document.sections), 4)
        self.assertEqual(document.sections[1].path, ["文档", "第一节", "子节1"])
        self.assertEqual(document.sections[3].path, ["文档", "第二节", "子节2"])


if __name__ == "__main__":
    unittest.main()
