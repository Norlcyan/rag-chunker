"""FastAPI service entrypoint for the Python chunking worker."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Sequence

import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from rag_chunker.pipeline import MARKDOWN_SUFFIXES, chunk_markdown_text


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
SUPPORTED_SOURCE_TYPE = "markdown"

app = FastAPI(title="rag-chunker Python Worker", version="0.1.0")


@app.post("/v1/chunk", response_model=None)
async def chunk_file(
    file: UploadFile = File(...),
    source_type: str = Form(SUPPORTED_SOURCE_TYPE),
) -> Any:
    """Chunk one uploaded Markdown file and return the HTTP-wrapped Chunk JSON."""
    normalized_source_type = source_type.strip().lower()
    if normalized_source_type != SUPPORTED_SOURCE_TYPE:
        return _error_response(f"Unsupported source_type: {source_type}", status_code=400)

    filename = _normalize_filename(file.filename)
    if not filename:
        return _error_response("Uploaded file must include a filename.", status_code=400)

    input_path = Path(filename)
    if input_path.suffix.lower() not in MARKDOWN_SUFFIXES:
        suffix = input_path.suffix or "<none>"
        return _error_response(f"Unsupported input type: {suffix}", status_code=400)

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
        payload = chunk_markdown_text(text, doc_id=input_path.stem)
    except UnicodeDecodeError as exc:
        return _error_response(f"Failed to decode uploaded file as UTF-8: {exc}", status_code=400)

    return {"status": "ok", **payload}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the rag-chunker FastAPI worker.")
    parser.add_argument("--host", default=os.getenv("RAG_CHUNKER_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("RAG_CHUNKER_PORT", str(DEFAULT_PORT))))
    args = parser.parse_args(argv)

    uvicorn.run("rag_chunker.server:app", host=args.host, port=args.port)
    return 0


def _normalize_filename(filename: str | None) -> str:
    if not filename:
        return ""
    return filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]


def _error_response(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"status": "error", "error": message})


if __name__ == "__main__":
    raise SystemExit(main())
