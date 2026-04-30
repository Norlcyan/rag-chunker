# API 接口文档

## 概述

本系统提供 RESTful API 接口，用于文档切片与检索增强生成（RAG）。

### 认证方式

所有接口需在 HTTP Header 中携带 `Authorization: Bearer <token>`。

```
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "******"
}
```

### 响应格式

统一响应格式如下：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误码说明见下表：

| 错误码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1001 | 认证失败 |
| 1002 | 参数错误 |

## 切片接口

### 上传文档

上传需要切片的文档文件。

```
POST /api/v1/chunk/upload
Content-Type: multipart/form-data

file: <binary>
max_section_level: 3
```

#### 支持格式

- Markdown（`.md` / `.markdown`）
- 未来支持：PDF、Word、HTML

#### 限制

- 单文件最大 50MB
- 单次最多处理 1000 个段落

### 查询切片结果

```python
import requests

resp = requests.get(
    "http://localhost:8080/api/v1/chunk/result/doc_001",
    headers={"Authorization": "Bearer xxx"}
)
chunks = resp.json()["data"]["chunks"]
```

### 删除切片缓存

~~~bash
curl -X DELETE \
  http://localhost:8080/api/v1/chunk/cache/doc_001 \
  -H "Authorization: Bearer xxx"
~~~

注意：~~~ 围栏与 ``` 围栏都会被正确解析，围栏内的 # 不会被误识别为 Markdown 标题。

## 配置参考

### 服务参数 ####

服务端口：8080，可通过环境变量 `PORT` 覆盖。

~~~yaml
chunker:
  max_section_level: 3
  min_chunk_size: 50
  enable_code_fence: true
~~~
