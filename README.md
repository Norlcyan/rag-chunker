# rag-chunker

A Java + Python toolkit for building reliable RAG document chunking pipelines, starting with Markdown structure-aware parsing and standardized Chunk JSON export.

## Project Status

This project is in the early MVP stage. The first milestone focuses on a minimal document chunking loop:

```text
Markdown document -> structure-aware chunking -> standardized Chunk JSON
```

The current scope is intentionally limited to the Python worker foundation, Markdown parsing, heading-aware chunking, and JSON export. Spring Boot services, databases, OCR, VLM, vector retrieval, and production indexing integrations are planned for later phases.

## Architecture Direction

The core pipeline follows this principle:

```text
Parser -> NormalizedDocument -> Chunker -> Enricher -> Exporter
```

Python is responsible for document parsing and chunk generation. Java services will later handle web APIs, task orchestration, authentication, persistence, and retrieval integration.

## Quick Start

Run the Markdown chunking MVP:

```bash
cd python-worker
python -m rag_chunker.cli ../samples/chunking_tool_design.md --out ../outputs/chunks.json
```

Run the test suite:

```bash
cd python-worker
python -m unittest discover -s tests
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
