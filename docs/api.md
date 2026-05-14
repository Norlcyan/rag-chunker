# HTTP API Contract

This document defines the current HTTP transport contract for the RAG chunking MVP.
For the Chunk JSON payload fields and generation rules, see [chunk-schema.md](chunk-schema.md).

Chinese version: [api.zh-CN.md](api.zh-CN.md).

## Scope

The current HTTP API is intentionally narrow:

- It chunks one uploaded Markdown file per request.
- It accepts `multipart/form-data`.
- It supports only `source_type = "markdown"`.
- It returns the existing Chunk JSON payload wrapped with HTTP status metadata.
- The Java Server stores successfully validated Chunk JSON synchronously.
- It does not create tasks, build indexes, or run batch processing.

Batch processing remains a CLI concern through `python-worker/rag_chunker/batch_cli.py`.

## Services

| Service | Default Address | Responsibility |
|---|---:|---|
| Java Server | `http://127.0.0.1:8080` | External entrypoint, request forwarding, successful response schema validation, synchronous Chunk storage. |
| Python Worker | `http://127.0.0.1:8000` | Markdown parsing, structure-aware chunking, HTTP-wrapped Chunk JSON generation. |

Java forwards `/v1/chunk` requests to the Python Worker. Java must not reimplement Markdown parsing, chunking, or JSON exporting logic.

## `POST /v1/chunk`

Chunks one uploaded Markdown document.

### Request

Content type:

```http
multipart/form-data
```

Form fields:

| Field | Type | Required | Description |
|---|---|---:|---|
| `file` | file | yes | One Markdown file. Current accepted suffixes are `.md` and `.markdown`. |
| `source_type` | string | no | Source type. Defaults to `markdown`; the current MVP rejects any other value. |

Example:

```bash
curl -X POST http://127.0.0.1:8080/v1/chunk \
  -F "file=@samples/simple_guide.md" \
  -F "source_type=markdown"
```

### Successful Response

HTTP status:

```http
200 OK
```

Body:

```json
{
  "status": "ok",
  "doc_id": "simple_guide",
  "doc_title": "简洁指南",
  "source_type": "markdown",
  "chunks": []
}
```

Rules:

- `status` is always `ok` for successful HTTP responses.
- `doc_id`, `doc_title`, `source_type`, and `chunks` follow the pure Chunk JSON schema.
- The Python pipeline and exporter still produce pure Chunk JSON without `status` or `error`.
- The Python HTTP layer adds `status = "ok"` at the top level and keeps the Chunk JSON fields unchanged.
- Empty Markdown content is valid and may return `chunks: []`.
- When Java is the external entrypoint, Java stores the validated `ChunkDocument` and `ChunkItem` records before returning `200 OK`.
- Database-generated ids and persistence status are not exposed in the HTTP response.

## Error Responses

All current error responses use this shape:

```json
{
  "status": "error",
  "error": "Human-readable error message."
}
```

### `400 Bad Request`

The Python Worker returns `400` for request-level validation failures. Java transparently forwards these responses when acting as the external entrypoint.

Examples:

| Scenario | HTTP Status | Example Error |
|---|---:|---|
| Unsupported source type | `400` | `Unsupported source_type: pdf` |
| Unsupported file suffix | `400` | `Unsupported input type: .txt` |
| Missing uploaded filename | `400` | `Uploaded file must include a filename.` |
| Uploaded content is not UTF-8 | `400` | `Failed to decode uploaded file as UTF-8: ...` |

### `502 Bad Gateway`

The Java Server returns `502` when it cannot safely return a Python Worker result to the caller.

Current `502` cases:

- The Python Worker is unavailable or the forwarding request fails.
- The Python Worker returns a `2xx` response whose body does not pass Java Chunk Schema validation.

Example:

```json
{
  "status": "error",
  "error": "Python worker request failed: chunks[0].chunk_id must be demo_chunk_0001."
}
```

### `500 Internal Server Error`

The Java Server returns `500` when the Python Worker returned valid Chunk JSON but Java failed to persist the validated document and chunks.

Example:

```json
{
  "status": "error",
  "error": "Chunk persistence failed."
}
```

## Java Validation Behavior

Java validates only successful Python HTTP responses.

Validation rules are based on [chunk-schema.md](chunk-schema.md), including:

- `status` must be `ok`.
- `source_type` must be `markdown`.
- `chunk_id` must follow `{doc_id}_chunk_{seq:04d}`.
- chunk `doc_id` must match the top-level `doc_id`.
- `section_path` must start with `doc_title`.
- `level = 0` must represent `__preamble__`.
- current MVP section levels are `0`, `2`, and `3`.
- `retrieval_text` must equal `" > ".join(section_path) + "\n\n" + text`.

The Java internal validation result is represented by `ChunkValidationResult`:

- valid response: `valid = true`, `document` is available, `errors` is empty.
- invalid response: `valid = false`, `document = null`, `errors` contains all collected validation errors.

`ChunkValidationResult` is an internal Java object. It is not part of the public HTTP response contract.

## Java Storage Behavior

Java stores only successful Python responses that pass Java Chunk Schema validation.

Storage rules:

- Python non-`2xx` responses are transparently forwarded and are not stored.
- Python `2xx` responses that fail Java validation return `502` and are not stored.
- Validated `ChunkDocument` and all `ChunkItem` rows are stored in one transaction.
- Repeated `doc_id` values are allowed; each successful upload creates a new database document row.
- `doc_id` remains the source file stem from the Python output and is not a database primary key.
- Chunk order is stored with an explicit `sequence_number`.
- `section_path` is stored as JSON text in the current MVP.
- Reference DDL is available at `java-server/src/main/resources/db/chunk-storage-schema.sql`.
- Spring SQL initialization is disabled by default; database preparation is an explicit local operation.

## Compatibility Notes

The current API does not include:

- task id
- schema version
- request id
- database id
- persistence status
- index status
- batch upload

Future API versions should keep existing response fields stable when possible and add optional fields only after the Chunk JSON contract is updated.
