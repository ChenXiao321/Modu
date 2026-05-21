# Story 1.2: 文档解析与结构化需求提取

Status: done

## Story

As a 嵌入式软件工程师,
I want 平台自动解析我上传的文档并提取结构化需求,
so that 我可以查看和审查芯片的功能需求和寄存器定义。

## Acceptance Criteria

1. [AC1] 文档上传完成后，平台自动触发解析任务（异步）。
2. [AC2] 标准格式 PDF/Word 解析成功率 ≥ 95%（以可提取文本为标准）。
3. [AC3] 解析结果以结构化需求条目呈现，每条包含：需求 ID、需求描述、来源文档章节、ASIL 等级（如声明）。
4. [AC4] 解析结果在 Web 界面以可浏览的树形结构展示。
5. [AC5] 工程师可通过解析任务 ID 查询解析进度和状态。

## Tasks / Subtasks

- [x] Task 1: 后端文档解析核心实现 (AC: 1,2,3,5)
  - [x] Subtask 1.1: 创建 `ParsedRequirement` 数据库模型（含 tenant_id、需求 ID、描述、章节、ASIL 等级、父需求 ID 支持树形结构）
  - [x] Subtask 1.2: 实现文本提取层 `TextExtractor`：支持 PDF（pdfplumber）、Word（python-docx）
  - [x] Subtask 1.3: 实现 `LLMClient` 抽象接口 + Mock 实现（用于 MVP 阶段展示结构化提取）
  - [x] Subtask 1.4: 实现 `DocumentParseService`：协调文本提取 → LLM 结构化提取 → 结果持久化
  - [x] Subtask 1.5: 实现 `POST /api/v1/documents/{document_id}/parse` 触发解析端点
  - [x] Subtask 1.6: 实现 `GET /api/v1/documents/{document_id}/parse/status` 查询解析进度
  - [x] Subtask 1.7: 实现 `GET /api/v1/documents/{document_id}/requirements` 获取解析结果（树形结构）
  - [x] Subtask 1.8: 实现异步解析任务（FastAPI BackgroundTasks，预留 Celery 接入点）

- [x] Task 2: 前端需求查看器实现 (AC: 4,5)
  - [x] Subtask 2.1: 创建 `DocumentListPage` 文档列表页（展示上传的文档及解析状态）
  - [x] Subtask 2.2: 创建 `RequirementViewerPage` 需求查看页（树形结构展示解析结果）
  - [x] Subtask 2.3: 实现解析进度轮询 Hook（`useParseProgress`）
  - [x] Subtask 2.4: 添加路由 `/documents`（列表）和 `/documents/:id/requirements`（查看器）
  - [x] Subtask 2.5: 上传完成后自动触发解析并跳转

- [x] Task 3: 测试与质量保障 (AC: 全部)
  - [x] Subtask 3.1: 后端单元测试：`TextExtractor` 对不同格式的提取
  - [x] Subtask 3.2: 后端单元测试：`DocumentParseService` 的协调逻辑
  - [x] Subtask 3.3: 后端集成测试：触发解析 → 查询进度 → 获取结果完整流程
  - [x] Subtask 3.4: 前端组件测试：树形组件渲染、进度轮询

### Review Findings

- [x] [Review][Decision→Patch] 缺少 Excel/PPT 文本提取，违反 PRD FR-REQ-001 — 用户决策：在 Story 1.2 范围内补全最简实现（openpyxl/python-pptx 基础文本提取）

- [x] [Review][Patch] execute_parse 静默吞掉所有异常，无日志/诊断信息 — 已修复：添加 logging，区分 TextExtractorError 和通用异常，保留错误上下文
- [x] [Review][Patch] 并发/重复解析任务竞争条件：无幂等性检查 — 已修复：trigger_parse 检查 parse_status != "running"；execute_parse 检查文档存在性和 storage_path
- [x] [Review][Patch] 自引用 FK 批量删除未配置级联 — 已修复：RequirementRepository.delete_by_document 先删子节点再删父节点
- [x] [Review][Patch] 递归持久化无事务隔离 — 已修复：添加 _validate_tree_depth 限制最大深度为 10；每个 req_repo.create 仍在单独 commit（MVP 阶段接受，后续引入显式事务）
- [x] [Review][Patch] TextExtractor 完全忽略 file_type 参数 — 已修复：_resolve_ext 优先使用 MIME type 映射，fallback 到扩展名
- [x] [Review][Patch] 提取前未校验文件存在性 — 已修复：extract() 开头检查 os.path.exists
- [x] [Review][Patch] PDF 扫描件/图片无文本时静默产生空输入 — 已修复：extract() 检查空文本并抛出 TextExtractorError
- [x] [Review][Patch] 损坏 docx 文件解析异常被 broad except 吞掉 — 已修复：TextExtractor 各方法捕获特定异常并包装为 TextExtractorError
- [x] [Review][Patch] get_parse_status 永远无法返回 "running" 状态 — 已修复：Document 模型新增 parse_status 字段，支持 pending/running/completed/failed
- [x] [Review][Patch] trigger_parse 对未完成的文档抛出 DocumentNotFoundError — 已修复：引入 DocumentNotReadyError，HTTP 映射为 409
- [x] [Review][Patch] useParseProgress Hook documentId 变化时不重置状态 — 已修复：添加 documentId 依赖的 useEffect，自动重置并重新轮询
- [x] [Review][Patch] _persist_requirements 直接访问 dict key — 已修复：使用 .get() 并显式校验 requirement_id 和 description 必填
- [x] [Review][Patch] 后台任务未重新验证租户/文档归属 — 已修复：_run_parse 中重新查询文档并校验 parse_status == "running"
- [x] [Review][Patch] useParseProgress 网络持续错误时无限轮询 — 已修复：添加 errorCount 计数，连续 5 次错误后自动停止轮询
- [x] [Review][Patch] DocumentUploader 自动触发解析失败时无任何用户反馈 — 已修复：.catch 中 setParseError，UI 显示警告 Alert
- [x] [Review][Patch] DocumentListPage 未处理 listDocuments API 错误 — 已修复：添加 catch 块和 Alert 错误提示
- [x] [Review][Patch] RequirementTree 递归渲染无深度限制 — 已修复：buildTreeData 添加 depth 参数，MAX_TREE_DEPTH = 10
- [x] [Review][Patch] upload_status 被重载表示解析状态 — 已修复：Document 模型新增 parse_status 字段，list_documents 直接使用 doc.parse_status
- [x] [Review][Patch] LLM 提取的 requirement_id 未做输入校验 — 已修复：_persist_requirements 校验长度 <= 50 且非空
- [x] [Review][Patch] 单元测试临时文件在断言失败时泄漏 — 已修复：使用 try/finally 包裹临时文件清理
- [x] [Review][Patch] TextExtractor 空 txt 文件返回 "" 给 LLM — 已修复：extract() 统一检查空文本并抛出 TextExtractorError
- [x] [Review][Patch] list_documents 使用 DocumentParseService 混合职责 — 已修复：list_documents 路由使用 DocumentService，DocumentService 新增 list_documents 方法

### Round 2 Review Findings (Post-Fix)

**High (1 fixed):**
- [x] [Review][Patch] `_run_parse` 异常处理缺口 — 已修复：添加外层 try/except，崩溃时将文档标记为 failed

**Medium (5 fixed):**
- [x] [Review][Patch] `execute_parse` 不检查 `parse_status` — 已修复：添加 `parse_status == "running"` 守卫
- [x] [Review][Patch] `trigger_parse` 允许对 completed 重新触发 — 已修复：检查 `parse_status == "completed"` 并拒绝
- [x] [Review][Patch] `DocumentUploader` `parseTriggered` 不重置 — 已修复：`beforeUpload` 重置 `parseTriggered` 和 `parseError`
- [x] [Review][Patch] `_persist_requirements` 注释与实现不一致 — 已修复：注释改为诚实描述（MVP 逐节点 commit）
- [x] [Review][Patch] `DocumentListPage` 不显示 "running" — 已修复：添加蓝色"解析中"标签

**Technical Debt (deferred):**
- [ ] [Review][Defer] `delete_by_document` N+1 删除 — deferred，当前文档规模下无性能问题
- [ ] [Review][Defer] `TextExtractor` 未校验文件大小 — deferred，上传层已有 100MB 限制
- [ ] [Review][Defer] `MockLLMClient` ID 碰撞 — deferred，Mock 实现非生产使用
- [ ] [Review][Defer] `get_parse_status` 硬编码进度 — deferred，需 BackgroundTasks 进度报告机制
- [ ] [Review][Defer] `RequirementTree` 无 memoization — deferred，当前树规模小
- [ ] [Review][Defer] `useParseProgress` 不暴露错误消息 — deferred，需扩展 API 返回错误详情
- [ ] [Review][Defer] `TextExtractor` `_extract_txt` `errors="ignore"` — deferred，编码问题待真实场景验证
- [ ] [Review][Defer] `schedule_parse` 与 FastAPI 紧耦合 — deferred，Celery 迁移时统一解耦

## Dev Notes

### 技术架构约束

- **多租户隔离**：`ParsedRequirement` 表必须包含 `tenant_id`；查询时必须按 tenant_id 过滤
- **异步处理**：MVP 阶段使用 FastAPI `BackgroundTasks` 执行解析，接口预留切换 Celery 的接入点
- **LLM 抽象**：`LLMClient` 为抽象基类，当前提供 `MockLLMClient` 实现（返回确定性模拟数据），后续替换为真实 LiteLLM 调用
- **文本提取**：PDF 优先使用 pdfplumber（保留段落结构），Word 使用 python-docx
- **树形结构**：`ParsedRequirement` 使用 `parent_requirement_id` 自引用实现树形；根节点 parent 为 null

### 项目结构对齐

**后端需创建/修改的文件：**
```
backend/app/
├── models/
│   └── parsed_requirement.py       # SQLAlchemy ParsedRequirement 模型 (NEW)
├── schemas/
│   └── requirements.py             # Pydantic DTOs for requirements (NEW)
├── repositories/
│   └── requirement_repository.py   # DB 访问层 (NEW)
├── routers/v1/
│   └── documents.py                # 追加解析相关端点 (MODIFY)
├── services/
│   ├── document_parse_service.py   # 解析协调服务 (NEW)
│   └── text_extractor.py           # 文本提取器 (NEW)
├── integrations/
│   └── llm_client.py               # LLM 抽象客户端 (NEW)
└── tasks/
    └── parse_document.py           # 异步解析任务 (NEW)
```

**前端需创建/修改的文件：**
```
frontend/src/
├── features/documents/
│   ├── pages/
│   │   ├── DocumentListPage.tsx    # 文档列表 (NEW)
│   │   └── RequirementViewerPage.tsx # 需求查看器 (NEW)
│   ├── components/
│   │   └── RequirementTree.tsx     # 树形需求组件 (NEW)
│   ├── hooks/
│   │   └── useParseProgress.ts     # 解析进度轮询 (NEW)
│   ├── types.ts                    # 追加 Requirement 类型 (MODIFY)
│   └── api.ts                      # 追加解析 API (MODIFY)
└── App.tsx                         # 追加路由 (MODIFY)
```

### API 设计规范

**标准响应格式（强制）：**
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "trace_id": "uuid"
}
```

**关键端点：**
- `POST /api/v1/documents/{document_id}/parse` → `{parse_task_id, status: "queued"}`
- `GET /api/v1/documents/{document_id}/parse/status` → `{document_id, status: "pending|running|completed|failed", progress_percent, message}`
- `GET /api/v1/documents/{document_id}/requirements` → `{requirements: [tree_nodes]}`
- `GET /api/v1/documents` → 查询当前租户文档列表（含解析状态）

**树形节点结构：**
```json
{
  "requirement_id": "SW-REQ-001",
  "description": "需求描述",
  "chapter": "3.2.1",
  "asil_level": "B",
  "children": []
}
```

### 数据库模型设计

**parsed_requirements 表：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 唯一标识 |
| tenant_id | INT FK | 租户隔离 |
| document_id | UUID FK | 关联 documents 表 |
| requirement_id | VARCHAR(50) | 需求编号（如 SW-REQ-001） |
| description | TEXT | 需求描述 |
| chapter | VARCHAR(100) | 来源章节 |
| asil_level | VARCHAR(10) | ASIL 等级（A/B/C/D 或 null） |
| parent_requirement_id | UUID FK | 父需求 ID（树形结构） |
| created_at | TIMESTAMPTZ | 创建时间 |

### 性能与安全要求

- **NFR-PERF-003**: AI 需求分析（单文档 ≤50 页）完成时间 ≤60 秒。MVP 阶段 Mock LLM 可在数秒内完成。
- **NFR-SEC-002**: 敏感文档原文不在前端持久存储，仅传递结构化需求数据。
- **NFR-SEC-013**: AI API 调用参数不包含客户敏感信息（当前 Mock 实现无此问题，真实 LLM 接入时需添加脱敏层）。

### 外部依赖

- **后端新增**: pdfplumber>=0.11.0, python-docx>=1.1.0
- **前端新增**: 无（Ant Design Tree 组件已内置）

### 已知限制与注意事项

- **Auth 模块尚未实现**：继续沿用 Story 1.1 的占位 `get_current_user` 和 `get_current_tenant`
- **LLM 为 Mock 实现**：当前返回确定性模拟数据，用于验证端到端流程。真实 LLM 集成在后续 Story 中替换
- **解析准确率 ≥95%**：此指标依赖真实 LLM 能力，Mock 阶段标记为已知限制
- **OCR 功能**：Story 1.4 专门处理扫描件/图片的 OCR，本 Story 仅处理原生文本 PDF/Word

### 实现顺序建议

1. 先完成后端数据库模型 + 迁移（或 SQLite 自动建表）
2. 实现文本提取器 `TextExtractor`（PDF/Word）
3. 实现 Mock LLM 客户端和解析服务
4. 实现解析 API 端点
5. 完成前端文档列表和需求树形组件
6. 测试贯穿全程
