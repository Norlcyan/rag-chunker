# 泛用切片工具设计方案

## 一、问题定义

RAG 的核心瓶颈在切片。切片不好，检索必崩。一个合格的切片工具需要解决三个核心矛盾：

| 矛盾 | 说明 |
|---|---|
| **语义完整性 vs 检索粒度** | 块太大上下文完整但检索不准，块太小语义碎片化 |
| **格式多样性 vs 统一输出** | 输入可能是 PDF/Word/HTML/Markdown/Excel，输出必须 Schema 统一 |
| **图片含关键信息但不可被文本检索** | 图表、架构图无法用关键词匹配，但不能丢掉 |

现有工具的普遍问题：固定长度切分切断语义、不做图片处理、跨页表格被截断、无上下文增强导致 chunk 独立不可理解。

---

## 二、核心架构：三层退化策略

不搞一刀切。按输入文档的结构化程度，从零成本到高成本逐层降级。

```
输入文档
    │
    ▼
┌─────────────────────────────────────────────┐
│  第1层：结构感知切分                         │
│  - 利用文档原生结构标记                       │
│  - 零 API 成本                               │
│  - 有显式结构 → 直接切 ✅ 退出                │
│  - 无结构 → 降级到第2层                       │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  第2层：语义切分                             │
│  - Embedding 相邻句相似度 → 骤降点=切点       │
│  - 成本：1次 embedding 调用                   │
│  - 语义边界清晰 → 按断点切 ✅ 退出             │
│  - 文本过长/边界模糊 → 降级到第3层             │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  第3层：LLM 全量切分 + 上下文增强              │
│  - LLM 通读全文 → 输出切点 + 切分理由          │
│  - 成本高，仅关键文档/前两层无法处理的文档走这里 │
└─────────────────────────────────────────────┘
```

### 三层选择决策树

```
文档有 Heading/标题层级？
├── 是 → 第1层（结构感知）
└── 否 → 文本有明显话题边界？
        ├── 是 → 第2层（语义切分）
        └── 否 → 第3层（LLM 全量）
```

### 成本对比

| 层级 | 每千页成本 | 质量 | 占比（预估） |
|---|---|---|---|
| 第1层 | ~$0 | 高（有结构时） | ~70% |
| 第2层 | ~$0.02 | 中高 | ~25% |
| 第3层 | ~$2-5 | 最高 | ~5% |

---

## 三、格式感知解析器

不同格式的结构特征不同，解析策略内聚到各自的 Parser，对上层暴露统一接口。

```python
ParserOutput = {
    "paragraphs": [
        {
            "text": "...",
            "style": "heading_1",       # heading_1/2/3 | body | table | figure | caption
            "position": {
                "page": 15,             # PDF/Word 有
                "line_start": 420,      # 行号
                "bbox": (x1, y1, x2, y2)  # PDF 坐标
            }
        },
        ...
    ],
    "images": [
        {
            "image_data": b"...",                   # 图片字节
            "nearby_text": "图3: Attention机制...",  # 最近标题/说明
            "page": 4,
            "bbox": (100, 200, 400, 500)
        },
        ...
    ],
    "tables": [...],
    "metadata": {
        "title": "Attention Is All You Need",
        "total_pages": 15,
        "format": "pdf"
    }
}
```

### 各格式的解析器

#### PDF

```
依赖：PyMuPDF (fitz)
策略：
  1. 逐页提取文字块 + 字号 + 坐标
  2. 字号聚类（最大 → 一级标题，次大 → 二级标题...）
  3. 坐标聚类（同一纵坐标区间 → 同级节点）
  4. 跨页段落检测（上一页最后一段无终止标点 + 下一页第一段开头小写）
  5. 图片检测：page.get_images() → 提取 + 坐标 → 匹配就近标题文字
  6. 表格检测：文字块密集排列 + 对齐网格特征
```

难点："看起来像标题但其实是加粗正文"——聚类结果不完美时需要第2层兜底验证。

#### Word (docx)

```
依赖：python-docx
策略：
  1. 直接读 paragraph.style（Heading 1/2/3 是显式的）
  2. 遇到非标题非正文字体变化 → 单独标记
  3. 图片：document.inline_shapes → 提取 + 匹配就近段落
  4. 表格：document.tables → 保留行列结构
```

最友好的格式，结构感知层直接出最优解。

#### Markdown

```
依赖：正则 + mistune（可选）
策略：
  - # → 一级，# → 二级，### → 三级，以此类推
  - 代码块 → 保留边界，函数/类内部不切
  - 图片 ![...](...) → 提取路径 + alt text
```

#### HTML

```
依赖：BeautifulSoup
策略：
  - <h1>-<h6> → 标题层级
  - <section>/<article>/<main> → 保留语义区块
  - <table> → 整体提取或转为 Markdown 表格
  - <img> → 提取 src/alt
  - <nav>/<footer>/<script>/<style> → 丢弃
```

#### Excel (xlsx)

```
依赖：openpyxl
策略：
  - 不按"章节"建索引，按 Sheet+区域 建 Schema
  - 每行 → 一条记录 → 按列名分组描述
  - 合并区域 → 保留合并边界
  - 输出格式从"章节树"转为"表格 Schema"
```

#### 纯文本

```
策略：
  - 空行 → 段落边界
  - 缩进/大写字母开头 → 可能的章节标志
  - 直接走第2层语义切分
```

---

## 四、图片处理策略

### 核心信条

**文本描述用于检索，原始图片用于回答。**

不能让模型只看"别人对图表的描述"来回答关于图表的问题——这相当于让一个没看过电影的人转述剧情。

### 处理流程

```
文档中的图片
    │
    ▼
检测 & 提取（各 Parser 实现）
  ├── 图片文件 → 本地保存
  ├── 定位信息 → 页码/附近文本/上下文
  └── 分级标记 → 信息密集型 or 装饰型
    │
    ▼
图片"转文本"（使图片可被文本检索命中）
  ├── 就近文本关联 → 0成本，取 caption/附近标题
  ├── OCR 文本提取 → 低成本，适合表格/数据图
  └── VLM 描述生成 → 高质量，适合关系图/架构图
    │
    ▼
打包进 chunk
  ├── text_content: OCR + VLM 描述 + 就近文本  ← 用于检索匹配
  └── raw_images:   [本地路径列表]              ← 用于回答时回传
    │
    ▼
回答时多模态回传
  └── 检索命中 chunk → LLM/VLM 同时收到（文本 + 原始图片）
```

### 图片分级

| 级别 | 类型 | 处理方式 | 示例 |
|---|---|---|---|
| 信息密集型 | 表格截图的图、数据线图、架构图、流程图、公式 | OCR + VLM 描述 + 原始图片保留 | 收入增长趋势图、Transformer 架构图 |
| 文本型 | 扫描件页面、文档拼页截图 | OCR 全文提取，图片可选返回 | 扫描版合同 |
| 修饰型 | Logo、装饰图、背景图 | 忽略 | 页眉装饰 |

### Chunk Schema 中的图片字段

```python
ImageEntry = {
    "local_path": "/data/doc_id/page_4_img_1.jpg",
    "caption": "Figure 2: Scaled Dot-Product Attention",
    "ocr_text": "MatMul Softmax Scale Mask ...",
    "vlm_description": "该图展示了缩放点积注意力的完整计算流程：输入QKV..."
    "image_type": "chart",      # chart | table | diagram | screenshot | photo | logo
    "importance": "critical",   # critical | informative | decorative
}
```

---

## 五、特殊场景处理

### 5.1 跨页表格

```
检测规则：
  - 页末出现表格且下一页开头是"表X（续）/Continued/续表"
  - 或：连续两页表头列名一致

处理：
  1. 合并跨页片段
  2. 整体 ≤ max_chunk_size → 完整保留
  3. 整体 > max_chunk_size → LLM 生成表格摘要，原始表格作为附件
```

### 5.2 跨页段落

```
检测规则：
  - 上一页最后一段无终止标点（。！？.!?）
  - 或：下一页第一段以小写字母开头

处理：
  - 合并为完整段落
  - 切分点调整到段落边界
```

### 5.3 代码块

```
规则：
  - 代码块内部不切分
  - 按函数/类/模块边界切
  - 用 AST 做代码段边界检测（非正则）
```

---

## 六、统一输出 Schema

```python
Chunk = {
    # ── 文本内容 ──
    "chunk_id": "doc001_page15_chunk03",
    "text": "The Transformer model architecture...",

    # ── 结构信息 ──
    "section_title": "3.2 Attention",
    "section_path": ["3 Model Architecture", "3.2 Attention"],
    "level": 2,                  # 标题层级（1-6，0=无层级）
    "page_range": [15, 18],
    "chunk_type": "section_text", # section_text | table | figure_group | code_block

    # ── 图片 ──
    "images": [
        {
            "local_path": "/data/page_15_img_1.jpg",
            "caption": "Figure 2: Scaled Dot-Product Attention",
            "ocr_text": "...",
            "vlm_description": "...",
            "image_type": "chart",
            "importance": "critical"
        }
    ],

    # ── 表格 ──
    "tables": [
        {
            "table_as_markdown": "| Q1 | 24.7 | ...",
            "table_caption": "表1: 季度收入"
        }
    ],

    # ── 上下文增强 ──
    "context_prefix": "本文档为'Attention Is All You Need'论文，"
                      "此段位于第15-18页，属于第3.2节'Attention'部分。",

    # ── 元数据 ──
    "doc_id": "doc001",
    "doc_title": "Attention Is All You Need",
    "prev_chunk_id": "doc001_page12_chunk02",
    "next_chunk_id": "doc001_page19_chunk01",
}
```

---

## 七、市面上成熟工具调研

### 7.1 结构感知路线

| 工具 | 语言 | 核心思路 | 亮点 |
|---|---|---|---|
| **Chunkr** (YC 投资) | Rust | 布局分析 → 段落级分段 | PDF 重灾区首选，RTX 4090 跑 ~4页/秒 |
| **Sycamore** (Aryn AI) | Python | DETR 模型做文档解析，8万+企业文档训练 | 号称比竞品准确 6 倍、召回翻倍 |
| **S2 Chunking** | Python | YOLO 布局检测 + BERT 语义 + 谱聚类 | arXiv/PubMed 上 0.92 凝聚力得分 |
| **Docling** + **Chonkie** | Python+Rust | Docling 做布局解析 → Chonkie 做语义切分 | 轻量组合，生产管线常用 |
| **poma-primecut-nano** | Python | Markdown 标题层级，保留完整祖先路径 | 零成本，技术文档极简方案 |
| **semantic-text-splitter** | Rust+Python | Markdown/代码切割，tree-sitter 语法感知 | 性能好，跨平台 |
| **Kallia** | Python | Docling 解析 PDF → 自动摘要 + Q&A 对 | 文档增强一体化 |

### 7.2 LLM 增强路线

| 工具 | 核心思路 | 成本 | 效果 |
|---|---|---|---|
| **MDKeyChunker** | 一次 LLM 调用提取 title/summary/keywords/QA等 7 个字段，滚动语义键去重 | ~75s/块 | Recall@5=1.0，MRR=0.911 |
| **lmchunker** | LLM 困惑度（PPL）检测自然文本边界，动态组合粗细粒度 | 按 token 计费 | 基于 Meta-Chunking 论文 |
| **RAG-Architect** (Apify) | 表格保护 + 父子上下文注入 + 自动 Q&A + PII 脱敏 | ~$0.07/URL | 12 种输出格式 |

### 7.3 专用场景

| 工具 | 场景 |
|---|---|
| **ragnar** (R) | R 生态用户，DuckDB + 混合检索 + MCP 服务 |
| **smart-ingest-kit** | 混合文档（PDF+代码+MD），Docling 布局感知，不同文件类型不同策略 |
| **VectraDB Chunkers** (Rust) | VectraDB 向量库生态原生 |
| **Docs-to-RAG Crawler** (Apify) | 文档站点一键爬取+切片，支持 Docusaurus/ReadTheDocs/GitBook |

### 7.4 与方案设计对照

| 本方案设计要点 | 已有对应工具 |
|---|---|
| 结构感知优先（第1层） | Chunkr / Sycamore / S2 / semantic-text-splitter |
| 语义切分降级（第2层） | Chonkie / lmchunker |
| LLM 全量切分+增强（第3层） | MDKeyChunker / RAG-Architect |
| 图片保留 + VLM 回传 | Chunkr（VLM per segment） |
| 表格/代码不切 | MDKeyChunker / RAG-Architect |
| 上下文前缀注入 | poma-primecut-nano（祖先路径） / RAG-Architect |
| 统一输出 Schema | **无一做到完全统一** |

### 7.5 与基础工具的对比

| 维度 | LangChain Splitter | LlamaIndex Splitter | Unstructured.io | 本方案 |
|---|---|---|---|---|
| **分块方式** | 固定/递归 | 固定/语义 | 结构感知 | 三层退化（结构→语义→LLM） |
| **多格式支持** | ❌ 纯文本 | ❌ 纯文本 | ✅ | ✅ |
| **图片处理** | ❌ | ❌ | 检测不描述 | ✅ 多模态描述 + 原始图片保留 |
| **跨页表格** | ❌ | ❌ | ❌ | ✅ |
| **上下文增强** | ❌ | ❌ | ❌ | ✅ |
| **LLM 依赖** | 无 | 可选 | 无 | 第3层需要 |

### 7.6 推荐组合策略

目前市面上没有一个工具能覆盖所有需求。最优策略是**组合现有工具 + 少量自研**：

```
Chunkr / Docling（PDF 布局解析，底层不造轮子）
    +
Chonkie / semantic-text-splitter（语义切分，轻量快速）
    +
MDKeyChunker 思路（LLM 增强，仅关键文档启用）
    +
自研：图片处理管道（检测 → OCR/VLM描述 → 回答时回传原图）
    +
自研：统一 Schema 适配层（对接不同上游，输出统一格式）
```

底层布局检测不要自研（Chunkr/Sycamore 的技术壁垒不是单人能复现的），上层切分策略和增强逻辑自己做。

---

## 八、推荐实现步骤

```
Phase 1: 文本管道
  ├── 实现 Markdown Parser（最简单，验证架构）
  ├── 实现 Word Parser（Heading 显式，验证结构感知效果最优）
  ├── 实现 PDF Parser（字号聚类 + 坐标检测）
  └── 统一输出 Schema

Phase 2: 切片引擎
  ├── 结构感知切片（第1层）
  ├── 语义切分（第2层）
  ├── LLM 切片（第3层）
  └── 上下文增强（前缀生成）

Phase 3: 图片 & 特殊场景
  ├── 图片检测 & 提取
  ├── OCR + VLM 描述管道
  ├── 跨页表格/段落处理
  └── 图片回传回答管道

Phase 4: 性能 & 验证
  ├── Bing-C 等基准评测切片质量
  ├── 大规模文档批量处理优化
  └── 切片结果回检 & 修正
```

---

## 九、关键设计决策总结

1. **结构优先，不做多余工作** — 文档有 Heading 就只用 Heading，不调 LLM
2. **文本用于检索，图片用于回答** — 图片转为文本是为了被搜索命中，回答时必传原图给多模态模型
3. **跨页内容必须合并** — 切分点在段落/表格逻辑边界，不在物理页边界
4. **每个 chunk 必须独立可理解** — 剥离文档名和章节路径后，chunk 应能自解释
5. **成本按需递进** — 大部分文档走第1层（0 成本），极端情况才走第3层
