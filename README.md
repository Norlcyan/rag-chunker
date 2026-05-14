# rag-chunker

A Java + Python toolkit for building reliable RAG document chunking pipelines, starting with Markdown structure-aware parsing and standardized Chunk JSON export.

## Project Status

This project is in the early MVP stage. The first milestone focuses on a minimal document chunking loop:

```text
Markdown document -> structure-aware chunking -> standardized Chunk JSON
```

The current scope covers the Python worker foundation, Markdown parsing, heading-aware chunking, JSON export, Java HTTP forwarding, Java schema validation, and synchronous storage of validated Chunk JSON. OCR, VLM, vector retrieval, and production indexing integrations are planned for later phases.

## Architecture Direction

The core pipeline follows this principle:

```text
Parser -> NormalizedDocument -> Chunker -> Enricher -> Exporter
```

Python is responsible for document parsing and chunk generation. Java handles the HTTP entrypoint, Python forwarding, successful response validation, and synchronous Chunk storage. Later phases will add task orchestration, authentication, and retrieval integration.

## Schema

The current MVP output contract is documented in [docs/chunk-schema.md](docs/chunk-schema.md).
The HTTP API contract is documented in [docs/api.md](docs/api.md), with a Chinese version at [docs/api.zh-CN.md](docs/api.zh-CN.md).

## Quick Start

Run the Markdown chunking MVP:

```bash
cd python-worker
python -m rag_chunker.cli ../samples/chunking_tool_design.md --out ../outputs/chunks.json
```

Run all sample Markdown documents:

```bash
cd python-worker
python -m rag_chunker.batch_cli ../samples --out-dir ../outputs
```

Install the Python worker service dependencies in a virtual environment:

```bash
cd python-worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install development and test dependencies:

```bash
cd python-worker
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the FastAPI chunking service:

```bash
cd python-worker
python -m rag_chunker.server --host 127.0.0.1 --port 8000
```

Chunk one Markdown file through HTTP:

```bash
curl -s -X POST http://127.0.0.1:8000/v1/chunk \
  -F "file=@../samples/simple_guide.md" \
  -F "source_type=markdown"
```

Run the Spring Boot Java server:

```bash
cd java-server
mvn spring-boot:run
```

Prepare the local MySQL schema from the repository root before calling the Java server successfully:

```bash
mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS rag_chunker DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -p123456 rag_chunker < java-server/src/main/resources/db/chunk-storage-schema.sql
```

Call the Java server chunk proxy:

```bash
curl -s -X POST http://127.0.0.1:8080/v1/chunk \
  -F "file=@../samples/simple_guide.md" \
  -F "source_type=markdown"
```

Run the test suite:

```bash
cd python-worker
python -m unittest discover -s tests

cd ../java-server
mvn test
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
