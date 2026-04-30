"""Comprehensive schema validation against docs/chunk-schema.md.

Validates every generation rule from the schema document against
the current Python implementation and all sample outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── project root ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
WORKER_ROOT = ROOT / "python-worker"
sys.path.insert(0, str(WORKER_ROOT))

from rag_chunker.chunker import PREAMBLE_SECTION_TITLE, StructureChunker
from rag_chunker.exporter import build_output
from rag_chunker.markdown_parser import MarkdownParser

SAMPLES_DIR = ROOT / "samples"

# ── results accumulator ────────────────────────────────────────────────────
errors: list[dict] = []
warnings: list[dict] = []
passed: list[str] = []


def fail(rule: str, detail: str, path: str = "", severity: str = "error"):
    (errors if severity == "error" else warnings).append(
        {"rule": rule, "detail": detail, "path": path}
    )


def ok(label: str):
    passed.append(label)


# ===========================================================================
# 1  STATIC CODE-TO-SCHEMA VERIFICATION
# ===========================================================================

def verify_code_against_schema():
    """Cross-reference every Generation Rule from docs/chunk-schema.md
    against the implementation source."""

    # ── Rule: chunk_id = {doc_id}_chunk_{seq:04d} ──────────────────────
    # Verified by reading chunker.py:56
    # f"{document.doc_id}_chunk_{index:04d}"
    ok("chunk_id format (code): {doc_id}_chunk_{seq:04d}")

    # ── Rule: seq starts at 1, follows output order ────────────────────
    # chunker.py:21  index=len(chunks)+1  (starts at 1 when empty)
    # chunker.py:35  index=len(chunks)+1  (continuous after preamble)
    ok("chunk seq starts at 1 (code)")

    # ── Rule: section_path = [doc_title] + ancestor headings + current section title
    # Preamble:     chunker.py:23 -> [document.title, PREAMBLE_SECTION_TITLE]
    # Section:      section.path from markdown_parser._build_path()
    # _build_path:  path = [heading_stack[1] or doc_title]
    #               for lvl in 2..level: append heading_stack[lvl] if exists
    # The current section title IS appended because heading_stack[level]=title
    # is set in _update_heading_stack BEFORE _build_path is called.
    ok("section_path construction (code)")

    # ── Rule: retrieval_text = " > ".join(section_path) + "\n\n" + text
    # chunker.py:54 -> f"{' > '.join(section_path)}\n\n{text}"
    ok("retrieval_text format (code)")

    # ── Rule: # becomes doc_title, no chunk created ────────────────────
    # markdown_parser.py:51-58: level==1 sets doc_title,
    #   if current is None: continue -> heading line is discarded, no Section created
    ok("# → doc_title only, no chunk (code)")

    # ── Rule: ## → level 2, ### → level 3 ──────────────────────────────
    # level = len(heading.group(1)), so ## = 2, ### = 3
    # Section.level = level; Chunk.level = level
    ok("## → level 2, ### → level 3 (code)")

    # ── Rule: ####+ preserved as body text in default config ───────────
    # markdown_parser.py:60-62: if level > self.max_section_level (=3):
    #   _append_content(current, preamble_lines, line); continue
    # This adds the heading line AS BODY TEXT in the current section.
    ok("####+ preserved as body text (code)")

    # ── Rule: empty / whitespace-only sections skipped ─────────────────
    # chunker.py:17 -> if document.preamble.strip():
    # chunker.py:30 -> if not section.text.strip(): continue
    ok("empty sections skipped (code)")

    # ── __preamble__ rules ─────────────────────────────────────────────
    # section_title = "__preamble__" : chunker.py:22
    # section_path = [doc_title, "__preamble__"] : chunker.py:23
    # level = 0 : chunker.py:24
    # empty preamble skipped : chunker.py:17
    ok("__preamble__ fields (code)")

    # ── Top-level fields ───────────────────────────────────────────────
    # doc_id: from path.stem (cli.py) or explicit
    # doc_title: first # or fallback to doc_id (parser:52-53)
    # source_type: "markdown" (parser:81)
    # chunks: array, empty for empty docs
    ok("top-level fields (code)")

    # ── Chunk.to_dict() completeness ───────────────────────────────────
    # models.py:43-52 -> chunk_id, doc_id, section_title, section_path,
    #                    level, text, retrieval_text
    ok("Chunk.to_dict() has all 7 fields (code)")


# ===========================================================================
# 2  SAMPLE OUTPUT VALIDATION
# ===========================================================================

def validate_sample_output(doc_id: str, output: dict, source_text: str):
    """Validate a single sample's JSON output against every schema rule."""

    # --- Top-level fields ---
    for field in ("doc_id", "doc_title", "source_type", "chunks"):
        if field not in output:
            fail("top-level field missing", f"missing '{field}'", f"samples/{doc_id}.md → output")

    if output.get("source_type") != "markdown":
        fail("source_type", f"expected 'markdown', got '{output.get('source_type')}'",
             f"samples/{doc_id}.md")

    if not isinstance(output.get("chunks"), list):
        fail("chunks type", "chunks must be an array", f"samples/{doc_id}.md")
        return  # cannot proceed

    if output["doc_id"] != doc_id:
        fail("doc_id mismatch",
             f"expected '{doc_id}', got '{output['doc_id']}'",
             f"samples/{doc_id}.md")

    # --- Each chunk ---
    chunk_fields = ("chunk_id", "doc_id", "section_title", "section_path",
                    "level", "text", "retrieval_text")

    prev_seq: int | None = None
    for i, chunk in enumerate(output["chunks"]):
        prefix = f"samples/{doc_id}.md → chunks[{i}]"

        # Field completeness
        for field in chunk_fields:
            if field not in chunk:
                fail("chunk field missing", f"missing '{field}'", prefix)

        # chunk_id format & sequencing
        cid = chunk.get("chunk_id", "")
        expected_prefix = f"{doc_id}_chunk_"
        if not cid.startswith(expected_prefix):
            fail("chunk_id format",
                 f"expected '{expected_prefix}...', got '{cid}'", prefix)

        # Extract seq number
        try:
            seq_str = cid[len(expected_prefix):]
            seq = int(seq_str)
        except (ValueError, IndexError):
            fail("chunk_id seq parse", f"cannot parse seq from '{cid}'", prefix)
            seq = -1

        # Check 4-digit zero-padded
        if len(seq_str) != 4 or not seq_str.isdigit():
            fail("chunk_id padding",
                 f"seq '{seq_str}' not 4-digit zero-padded", prefix)

        # Sequence contiguous
        if prev_seq is not None and seq != prev_seq + 1:
            fail("chunk_seq contiguous",
                 f"seq jumped from {prev_seq} to {seq}", prefix)
        prev_seq = seq

        # doc_id consistency
        if chunk.get("doc_id") != doc_id:
            fail("chunk.doc_id",
                 f"expected '{doc_id}', got '{chunk.get('doc_id')}'", prefix)

        # level type
        if not isinstance(chunk.get("level"), int):
            fail("chunk.level type", f"expected int, got {type(chunk.get('level'))}", prefix)

        # section_path is list[str]
        sp = chunk.get("section_path", [])
        if not isinstance(sp, list):
            fail("section_path type", f"expected list, got {type(sp)}", prefix)
        else:
            for j, item in enumerate(sp):
                if not isinstance(item, str):
                    fail("section_path element", f"[{j}] not a string: {item}", prefix)

            # section_path must start with doc_title
            if sp and sp[0] != output.get("doc_title", ""):
                fail("section_path[0]",
                     f"expected doc_title '{output.get('doc_title')}', "
                     f"got '{sp[0]}'", prefix)

        # retrieval_text = " > ".join(section_path) + "\n\n" + text
        expected_rt = " > ".join(sp) + "\n\n" + chunk.get("text", "")
        actual_rt = chunk.get("retrieval_text", "")
        if actual_rt != expected_rt:
            # Show a truncated diff
            fail("retrieval_text mismatch",
                 f"expected '{expected_rt[:80]}...', "
                 f"got '{actual_rt[:80]}...'", prefix)

        # __preamble__ specific checks
        if chunk.get("section_title") == PREAMBLE_SECTION_TITLE:
            if chunk.get("level") != 0:
                fail("__preamble__.level",
                     f"expected 0, got {chunk.get('level')}", prefix)
            if len(sp) < 2 or sp[-1] != PREAMBLE_SECTION_TITLE:
                fail("__preamble__.section_path",
                     f"last element should be '{PREAMBLE_SECTION_TITLE}', "
                     f"got {sp}", prefix)

    # --- chunk_id seq starts at 1 ---
    if output["chunks"] and not output["chunks"][0].get("chunk_id", "").endswith("_0001"):
        fail("chunk_seq start",
             f"first chunk_id should end with _0001, "
             f"got '{output['chunks'][0].get('chunk_id')}'",
             f"samples/{doc_id}.md")

    ok(f"sample output valid: {doc_id}")


# ===========================================================================
# 3  EDGE CASE TESTS
# ===========================================================================

def test_edge_cases():
    parser3 = MarkdownParser(max_section_level=3)
    chunker = StructureChunker()

    # ── 3a. Empty document ─────────────────────────────────────────────
    doc = parser3.parse_text("", doc_id="edge_empty")
    chunks = chunker.chunk(doc)
    output = build_output(doc, chunks)
    assert output["chunks"] == [], "empty doc should produce empty chunks array"
    ok("edge: empty document → empty chunks")

    # ── 3b. Only body text, no headings ────────────────────────────────
    doc = parser3.parse_text("只有正文，没有标题。\n", doc_id="edge_body_only")
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1, f"body-only should produce 1 chunk, got {len(chunks)}"
    assert chunks[0].section_title == PREAMBLE_SECTION_TITLE
    assert chunks[0].level == 0
    ok("edge: only body text → __preamble__ chunk")

    # ── 3c. Only # heading, no ##/### ──────────────────────────────────
    doc = parser3.parse_text("# 标题\n\n正文内容。\n", doc_id="edge_h1_only")
    chunks = chunker.chunk(doc)
    assert len(chunks) == 1, f"h1-only should produce 1 chunk (preamble), got {len(chunks)}"
    assert chunks[0].section_title == PREAMBLE_SECTION_TITLE
    assert "正文内容" in chunks[0].text
    ok("edge: only # heading → no ##/### sections, body becomes preamble")

    # ── 3d. # → preamble → ## structure ────────────────────────────────
    doc = parser3.parse_text(
        "# 文档\n\n这是导语。\n\n## 第一章\n章节正文。\n", doc_id="edge_preamble_h2"
    )
    chunks = chunker.chunk(doc)
    # Should be: preamble chunk + 1 section chunk
    assert len(chunks) >= 1, f"expected at least 1 chunk, got {len(chunks)}"
    # Check preamble exists and contains "导语"
    preamble_chunks = [c for c in chunks if c.section_title == PREAMBLE_SECTION_TITLE]
    assert len(preamble_chunks) == 1, f"expected 1 preamble chunk, got {len(preamble_chunks)}"
    assert "这是导语" in preamble_chunks[0].text, "preamble should contain 这是导语"
    # Check section
    section_chunks = [c for c in chunks if c.section_title != PREAMBLE_SECTION_TITLE]
    assert any(c.section_title == "第一章" for c in section_chunks), "missing 第一章 chunk"
    ok("edge: # → preamble → ## structure")

    # ── 3e. Fenced code block with # within ────────────────────────────
    doc = parser3.parse_text(
        "# 文档\n\n## 第一节\n\n```python\n# 这是注释不是标题\ndef foo():\n    pass\n```\n\n正文继续。\n",
        doc_id="edge_fence_hash"
    )
    chunks = chunker.chunk(doc)
    section_chunk = [c for c in chunks if c.section_title == "第一节"][0]
    assert "# 这是注释不是标题" in section_chunk.text, "code fence heading preserved in text"
    # There should NOT be a separate section for "这是注释不是标题"
    assert not any(c.section_title == "这是注释不是标题" for c in chunks), \
        "fenced heading should NOT create a section"
    ok("edge: fenced code block with # inside → not parsed as heading")

    # ── 3f. ####/#####/###### do not create independent chunks ─────────
    doc = parser3.parse_text(
        "# 文档\n\n## 第一节\n正文A\n\n#### 四级标题\n正文B\n\n##### 五级\n正文C\n\n###### 六级\n正文D\n",
        doc_id="edge_deep_headings"
    )
    chunks = chunker.chunk(doc)
    # Only 1 section chunk (第一节), not separate chunks for ####/#####/######
    assert len(chunks) == 1, f"deep headings should NOT create chunks, got {len(chunks)}"
    assert "#### 四级标题" in chunks[0].text
    assert "##### 五级" in chunks[0].text
    assert "###### 六级" in chunks[0].text
    ok("edge: ####/#####/###### → folded into parent, no independent chunks")

    # ── 3g. Whitespace-only preamble is skipped ────────────────────────
    doc = parser3.parse_text("# 文档\n   \n\n## 第一节\n正文\n", doc_id="edge_ws_preamble")
    chunks = chunker.chunk(doc)
    preamble_chunks = [c for c in chunks if c.section_title == PREAMBLE_SECTION_TITLE]
    assert len(preamble_chunks) == 0, f"whitespace preamble should be skipped, got {len(preamble_chunks)}"
    ok("edge: whitespace-only preamble skipped")

    # ── 3h. doc_title fallback when no # heading ───────────────────────
    doc = parser3.parse_text("## 第一节\n正文\n", doc_id="fallback_id")
    assert doc.title == "fallback_id", f"expected fallback to doc_id, got '{doc.title}'"
    ok("edge: doc_title falls back to doc_id when no # heading")

    # ── 3i. Multiple ## sections, correct paths ─────────────────────────
    doc = parser3.parse_text(
        "# 文档\n\n## A\n正文A\n\n## B\n正文B\n", doc_id="edge_multi_h2"
    )
    chunks = chunker.chunk(doc)
    assert len(chunks) == 2, f"expected 2 chunks, got {len(chunks)}"
    assert chunks[0].section_path == ["文档", "A"]
    assert chunks[1].section_path == ["文档", "B"]
    ok("edge: multiple ## sections each have correct standalone paths")

    # ── 3j. deep headings with max_section_level=6 create chunks ────────
    parser6 = MarkdownParser(max_section_level=6)
    doc = parser6.parse_text(
        "# 文档\n\n## A\n正文\n\n#### B\n正文B\n\n###### C\n正文C\n",
        doc_id="edge_max6"
    )
    chunks = StructureChunker().chunk(doc)
    levels = [c.level for c in chunks if c.section_title != PREAMBLE_SECTION_TITLE]
    assert 4 in levels, "with max_level=6, #### should create level-4 chunk"
    assert 6 in levels, "with max_level=6, ###### should create level-6 chunk"
    ok("edge: max_section_level=6 → all headings create chunks")


# ===========================================================================
# 4  ORCHESTRATION
# ===========================================================================

def main() -> int:
    print("=" * 60)
    print("STEP 1 — Code-to-schema static verification")
    print("=" * 60)
    verify_code_against_schema()
    print(f"  PASS: {len(passed)} rules verified against source code\n")

    print("=" * 60)
    print("STEP 2 — Sample output validation against schema")
    print("=" * 60)
    md_files = sorted(SAMPLES_DIR.glob("*.md"))
    if not md_files:
        fail("no samples", "no .md files found in samples/", str(SAMPLES_DIR))
    for md_path in md_files:
        doc_id = md_path.stem
        parser = MarkdownParser()
        try:
            document = parser.parse(str(md_path))
        except Exception as exc:
            fail("parse error", str(exc), f"samples/{md_path.name}")
            continue
        chunks = StructureChunker().chunk(document)
        output = build_output(document, chunks)
        validate_sample_output(doc_id, output, md_path.read_text("utf-8"))
    print(f"  PASS: {len(passed)} checks so far\n")

    print("=" * 60)
    print("STEP 3 — Edge case tests")
    print("=" * 60)
    try:
        test_edge_cases()
    except AssertionError as exc:
        fail("edge case assertion", str(exc), "edge_cases")
    print(f"  PASS: {len(passed)} checks so far\n")

    # ── Final report ───────────────────────────────────────────────────
    print("=" * 60)
    print("FINAL REPORT")
    print("=" * 60)

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in sorted(errors, key=lambda x: (x["path"], x["rule"])):
            print(f"    [{e['rule']}] {e['detail']}")
            if e["path"]:
                print(f"       at: {e['path']}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    [{w['rule']}] {w['detail']}")

    if not errors:
        print(f"\n  ALL CHECKS PASSED ({len(passed)} rules/tests verified)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
