# HTTP API 中文说明

本文面向中文用户，说明当前 RAG Chunker MVP 的 HTTP 接口、Java 校验与同步落库行为。Chunk JSON 字段和生成规则以 [chunk-schema.md](chunk-schema.md) 为准。

## 当前范围

当前 HTTP API 只覆盖最小闭环：

- 每次请求切片一个 Markdown 文件。
- 请求格式为 `multipart/form-data`。
- 仅支持 `source_type = "markdown"`。
- Python Worker 负责 Markdown 解析、结构切片和 Chunk JSON 生成。
- Java Server 作为外部入口，负责转发请求、校验 Python 成功响应，并同步保存校验后的 Chunk 数据。
- 当前不提供任务 ID、异步任务状态、索引状态、批量上传、Word/PDF/HTML 解析。

## 服务职责

| 服务 | 默认地址 | 职责 |
|---|---:|---|
| Java Server | `http://127.0.0.1:8080` | 外部入口、请求转发、成功响应校验、同步落库 |
| Python Worker | `http://127.0.0.1:8000` | Markdown 解析、结构感知切片、HTTP 响应封装 |

Java 不重新实现 Markdown 解析、切片或 JSON 导出逻辑。

## `POST /v1/chunk`

切片一个上传的 Markdown 文件。

### 请求

Content-Type：

```http
multipart/form-data
```

表单字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `file` | file | 是 | 一个 Markdown 文件。当前支持 `.md` 和 `.markdown`。 |
| `source_type` | string | 否 | 来源类型。默认 `markdown`，当前 MVP 拒绝其他值。 |

示例：

```bash
curl -X POST http://127.0.0.1:8080/v1/chunk \
  -F "file=@samples/simple_guide.md" \
  -F "source_type=markdown"
```

## 成功响应

HTTP 状态：

```http
200 OK
```

响应体：

```json
{
  "status": "ok",
  "doc_id": "simple_guide",
  "doc_title": "简洁指南",
  "source_type": "markdown",
  "chunks": []
}
```

规则：

- 成功响应的 `status` 固定为 `ok`。
- `doc_id`、`doc_title`、`source_type`、`chunks` 遵循纯 Chunk JSON 契约。
- Python pipeline/exporter 输出纯 Chunk JSON，不包含 `status` 或 `error`。
- Python HTTP 层只在顶层添加 `status = "ok"`。
- Java 作为外部入口时，会先保存已校验的 `ChunkDocument` 和 `ChunkItem`，再返回 `200 OK`。
- 数据库主键、落库状态、任务 ID 不暴露在 HTTP 响应中。

## 错误响应

当前错误响应统一使用：

```json
{
  "status": "error",
  "error": "Human-readable error message."
}
```

### `400 Bad Request`

Python Worker 对请求级错误返回 `400`。Java 作为代理入口时透明转发。

| 场景 | HTTP 状态 | 示例错误 |
|---|---:|---|
| 不支持的 `source_type` | `400` | `Unsupported source_type: pdf` |
| 不支持的文件后缀 | `400` | `Unsupported input type: .txt` |
| 上传文件缺少文件名 | `400` | `Uploaded file must include a filename.` |
| 上传内容不是 UTF-8 | `400` | `Failed to decode uploaded file as UTF-8: ...` |

### `502 Bad Gateway`

Java 在无法安全返回 Python 成功结果时返回 `502`。

当前场景：

- Python Worker 不可用，或请求 Python Worker 失败。
- Python Worker 返回 `2xx`，但响应体没有通过 Java Chunk Schema 校验。

示例：

```json
{
  "status": "error",
  "error": "Python worker request failed: chunks[0].chunk_id must be demo_chunk_0001."
}
```

### `500 Internal Server Error`

Python 返回合法 Chunk JSON，且 Java 校验成功，但 Java 同步落库失败时返回 `500`。

示例：

```json
{
  "status": "error",
  "error": "Chunk persistence failed."
}
```

## Java 校验行为

Java 只校验 Python 的成功响应。

主要校验规则：

- `status` 必须为 `ok`。
- `source_type` 必须为 `markdown`。
- `chunk_id` 必须符合 `{doc_id}_chunk_{seq:04d}`。
- chunk 内部 `doc_id` 必须等于顶层 `doc_id`。
- `section_path` 必须以 `doc_title` 开头。
- `level = 0` 必须表示 `__preamble__`。
- 当前 MVP 仅允许 `level = 0`、`2`、`3`。
- `retrieval_text` 必须等于 `" > ".join(section_path) + "\n\n" + text`。

`ChunkValidationResult` 是 Java 内部对象，不属于公开 HTTP 响应契约。

## Java 落库行为

Java 只保存通过校验的成功响应。

落库规则：

- Python 非 `2xx` 响应不落库，Java 透明转发。
- Python `2xx` 但 Java 校验失败时不落库，Java 返回 `502`。
- 校验通过后，`ChunkDocument` 和所有 `ChunkItem` 在同一事务中写入。
- 重复 `doc_id` 允许存在；每次成功上传都会生成新的数据库 document 记录。
- `doc_id` 来源于 Python 输出，当前通常是上传文件名去掉扩展名后的 stem，不作为数据库主键。
- chunk 顺序通过 `sequence_number` 单独保存。
- `section_path` 当前以 JSON 文本保存。

参考建表 SQL：

```text
java-server/src/main/resources/db/chunk-storage-schema.sql
```

Spring SQL 初始化默认关闭。数据库创建和表结构初始化是显式的本地准备步骤，不会随应用启动自动执行。

## 本地 MySQL 准备

在仓库根目录执行：

```bash
mysql -uroot -p123456 -e "CREATE DATABASE IF NOT EXISTS rag_chunker DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -p123456 rag_chunker < java-server/src/main/resources/db/chunk-storage-schema.sql
```

默认 Java 配置：

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/rag_chunker?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai
    username: root
    password: 123456
```

也可以通过环境变量覆盖：

```text
RAG_CHUNKER_DATASOURCE_URL
RAG_CHUNKER_DATASOURCE_USERNAME
RAG_CHUNKER_DATASOURCE_PASSWORD
```

## 当前不包含

当前 HTTP API 不包含：

- `task_id`
- `schema_version`
- `request_id`
- `database_id`
- `persistence_status`
- `index_status`
- 批量上传

这些字段未来如果需要暴露，应先更新公开 API 契约。
