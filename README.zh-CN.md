# rag-chunker

[English](README.md) | [简体中文](README.zh-CN.md)

rag-chunker 是一个 Java + Python 混合架构的 RAG 文档切片工具，当前从 Markdown 结构感知解析和标准化 Chunk JSON 导出开始，逐步建设稳定的文档切片流水线。

## 项目状态

项目目前处于早期 MVP 阶段。第一阶段聚焦最小文档切片闭环：

```text
Markdown 文档 -> 结构感知切片 -> 标准 Chunk JSON
```

当前范围包括 Python Worker 基础能力、Markdown 解析、标题感知切片、JSON 导出、Java HTTP 转发、Java schema 校验，以及已校验 Chunk JSON 的同步落库。OCR、VLM、向量检索和生产级索引集成计划在后续阶段推进。

## 架构方向

核心流水线遵循：

```text
Parser -> NormalizedDocument -> Chunker -> Enricher -> Exporter
```

Python 负责文档解析和切片生成。Java 负责 HTTP 入口、转发 Python Worker、校验成功响应，以及同步保存 Chunk 结果。后续阶段会补充任务编排、认证鉴权和检索集成。

## 契约文档

当前 MVP 输出契约见 [docs/chunk-schema.md](docs/chunk-schema.md)。
HTTP API 契约见 [docs/api.md](docs/api.md)，中文版本见 [docs/api.zh-CN.md](docs/api.zh-CN.md)。

## 快速开始

运行 Markdown 切片 MVP：

```bash
cd python-worker
python -m rag_chunker.cli ../samples/chunking_tool_design.md --out ../outputs/chunks.json
```

运行全部样例 Markdown 文档：

```bash
cd python-worker
python -m rag_chunker.batch_cli ../samples --out-dir ../outputs
```

在虚拟环境中安装 Python Worker 服务依赖：

```bash
cd python-worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

安装开发和测试依赖：

```bash
cd python-worker
source .venv/bin/activate
pip install -r requirements-dev.txt
```

启动 FastAPI 切片服务：

```bash
cd python-worker
python -m rag_chunker.server --host 127.0.0.1 --port 8000
```

通过 HTTP 切分一个 Markdown 文件：

```bash
curl -s -X POST http://127.0.0.1:8000/v1/chunk \
  -F "file=@../samples/simple_guide.md" \
  -F "source_type=markdown"
```

启动 Spring Boot Java 服务：

```bash
cd java-server
mvn spring-boot:run
```

调用 Java 服务前，先从仓库根目录准备本地 MySQL schema：

```bash
mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS rag_chunker DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -p123456 rag_chunker < java-server/src/main/resources/db/chunk-storage-schema.sql
```

调用 Java 服务的切片代理接口：

```bash
curl -s -X POST http://127.0.0.1:8080/v1/chunk \
  -F "file=@../samples/simple_guide.md" \
  -F "source_type=markdown"
```

运行测试套件：

```bash
cd python-worker
python -m unittest discover -s tests

cd ../java-server
mvn test
```

## 许可证

本项目使用 Apache License 2.0。详情见 [LICENSE](LICENSE)。
