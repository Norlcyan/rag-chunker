# 产品规格 v2.3

## 系统架构

### 前端

#### 技术栈

- **语言**：TypeScript 5.x
- **框架**：React 18 + Next.js 14
- **构建**：Turbopack

###### 微前端子模块

若采用微前端架构，每个子模块独立部署：

- 主控制台：`console.example.com`
- 数据看板：`dashboard.example.com`
- 配置中心：`config.example.com`

##### 路由设计 #####

使用 Next.js App Router，按功能域划分：

```
/app
  /dashboard
  /settings
  /chunk-viewer
```

### 后端

#### 技术栈

- **语言**：Java 17
- **框架**：Spring Boot 3.2
- **数据库**：MySQL 8

#### 接口规范

所有响应包裹在统一格式中。

###### 内部调用

微服务间通过 gRPC 通信。

注意：##### 和 ###### 级别的标题默认不产生独立切片，其内容会保留在父章节的正文中。

### 部署

#### 容器化

使用 Docker Compose 编排：

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]

  backend:
    build: ./backend
    ports: ["8080:8080"]
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/app
```
