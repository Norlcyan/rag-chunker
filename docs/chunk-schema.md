# Chunk JSON Schema

This document defines the current MVP output contract for Markdown structure-aware chunking.

The schema is intentionally small and stable. Java services can use it to validate Python worker output before persistence, indexing, or retrieval integration.

## Top-Level Object

```json
{
  "doc_id": "chunking_tool_design",
  "doc_title": "泛用切片工具设计方案",
  "source_type": "markdown",
  "chunks": []
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `doc_id` | string | yes | Stable document id. In the current CLI, this is the input file stem. |
| `doc_title` | string | yes | Document title. For Markdown, this comes from the first `#` heading when present; otherwise it falls back to `doc_id`. |
| `source_type` | string | yes | Source format. Current MVP value is `markdown`. |
| `chunks` | array | yes | Ordered list of chunk objects. Empty array is valid for empty documents. |

## Chunk Object

```json
{
  "chunk_id": "chunking_tool_design_chunk_0001",
  "doc_id": "chunking_tool_design",
  "section_title": "一、问题定义",
  "section_path": ["泛用切片工具设计方案", "一、问题定义"],
  "level": 2,
  "text": "RAG 的核心瓶颈在切片...",
  "retrieval_text": "泛用切片工具设计方案 > 一、问题定义\n\nRAG 的核心瓶颈在切片..."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `chunk_id` | string | yes | Unique chunk id within the generated output. |
| `doc_id` | string | yes | Same value as the top-level `doc_id`. |
| `section_title` | string | yes | Current section title. Uses `__preamble__` for untitled preamble content. |
| `section_path` | string[] | yes | Ordered structural path from document title to current section. |
| `level` | integer | yes | Markdown heading level. `0` means untitled preamble content. |
| `text` | string | yes | Raw Markdown text content for retrieval and downstream processing. |
| `retrieval_text` | string | yes | Context-enhanced text used for retrieval. |

## Generation Rules

- `chunk_id` is generated as `{doc_id}_chunk_{seq:04d}`.
- Chunk sequence starts at `1` and follows output order.
- `section_path` is generated as `[doc_title] + existing ancestor headings + current section title`.
- `retrieval_text` is generated as `" > ".join(section_path) + "\n\n" + text`.
- Markdown heading mapping:
  - `#` becomes `doc_title` and does not create a chunk by itself.
  - `##` creates a section with `level = 2`.
  - `###` creates a section with `level = 3`.
  - `####` and deeper headings are preserved as body text in the current MVP.
- Empty or whitespace-only sections are skipped and do not create chunks.

## `__preamble__`

`__preamble__` represents untitled body text before the first structural section.

For `__preamble__` chunks:

```json
{
  "section_title": "__preamble__",
  "section_path": ["文档标题", "__preamble__"],
  "level": 0
}
```

Rules:

- `level = 0` means the chunk does not correspond to a Markdown heading.
- Empty or whitespace-only preamble content is skipped.
- Java validation should not compare `level = 0` chunks against heading hierarchy rules.

## HTTP API Response

`POST /v1/chunk` wraps the pure Chunk JSON payload for HTTP transport.

Successful response:

```json
{
  "status": "ok",
  "doc_id": "simple_guide",
  "doc_title": "快速使用指南",
  "source_type": "markdown",
  "chunks": []
}
```

Error response:

```json
{
  "status": "error",
  "error": "Unsupported source_type: pdf"
}
```

Rules:

- The Python pipeline and exporter still produce pure Chunk JSON without `status` or `error`.
- The HTTP response adds `status = "ok"` at the top level and keeps the Chunk JSON fields unchanged.
- Error responses use `status = "error"` and a human-readable `error` message.
- The current MVP only accepts `source_type = "markdown"`.

## MVP Limitations

The current MVP does not include these fields:

| Field | Planned Meaning |
|---|---|
| `page_range` | Source page span for PDF/Word documents. |
| `images` | Extracted or linked image metadata. |
| `tables` | Structured table payloads or Markdown table representations. |
| `context_prefix` | Separate context prefix field when retrieval text generation becomes configurable. |

Future versions should add optional fields when possible. Existing field names and meanings should remain stable unless a schema versioning mechanism is introduced.

## Validation

Run the schema validation helper from `python-worker`:

```bash
python tests/validate_schema.py
```

The helper checks the documented generation rules against the current Python implementation, validates all sample Markdown outputs, and runs targeted edge case checks for preamble, heading levels, code fences, and deep headings.
