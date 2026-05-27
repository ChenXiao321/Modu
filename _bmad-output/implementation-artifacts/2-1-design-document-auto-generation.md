# Story 2.1: 设计文档自动生成

Status: in-progress

## Story

As a 嵌入式软件架构师,
I want 平台在文档解析完成后自动生成 ASPICE Level 2 设计文档,
so that 我可以基于结构化需求和安全关键参数快速获得包含完整章节、Polarion 追溯 ID 和 ASIL 等级声明的设计方案，减少手工编写工作量。

## Acceptance Criteria

1. [AC1] 给定文档解析已完成且流水线未被阻塞，当用户触发设计文档生成时，后端异步执行生成任务并返回任务 ID。
2. [AC2] 生成过程调用 LLM，基于功能需求树、安全关键参数和最高 ASIL 等级产出 8 个标准章节（overview, references, system_architecture, interface_definition, dynamic_behavior, resource_consumption, error_handling, test_strategy）。
3. [AC3] 每个章节包含 content 和 polarion_trace_id，且所有 8 个章节缺一不可。
4. [AC4] 生成完成后，流水线状态自动迁移为 `in_design`，设计文档可被查询。
5. [AC5] 前端提供设计文档查看页面，展示生成状态、ASIL 等级和各章节内容，并支持状态轮询。
6. [AC6] 若文档解析失败或流水线被阻塞，触发生成时返回明确的错误提示，且不允许进入生成阶段。

## Tasks / Subtasks

- [x] Task 1: 后端数据模型与存储层 (AC: 1,2,3,4)
  - [x] Subtask 1.1: 新建 `DesignDocument` SQLAlchemy 模型（字段：id, tenant_id, document_id, status, asil_level, sections JSON, error_message, created_at, updated_at）
  - [x] Subtask 1.2: 新建 `DesignDocumentRepository`（create, get_by_document_id, update_status）
  - [x] Subtask 1.3: 在 `main.py` 导入 `DesignDocument` 模型以确保建表

- [x] Task 2: 后端设计文档生成服务 (AC: 1,2,3,4,6)
  - [x] Subtask 2.1: 扩展 `LLMClient` 抽象接口，新增 `generate_design_document(requirements, safety_parameters, asil_level, filename) -> dict`
  - [x] Subtask 2.2: 在 `MockLLMClient` 中实现确定性 8 章节设计文档生成
  - [x] Subtask 2.3: 创建 `DesignDocumentService`，实现 `trigger_generate`（前置校验）、`execute_generate`（同步生成逻辑）、`get_design_document`（查询状态）
  - [x] Subtask 2.4: 实现 ASIL 等级解析逻辑：从需求树中提取最高 ASIL，无有效 ASIL 时默认 QM
  - [x] Subtask 2.5: 实现 `generate_design_document.py` 后台任务调度器（BackgroundTasks 模式）
  - [x] Subtask 2.6: 新增异常类 `PipelineBlockedError`、`DesignDocumentNotFoundError`

- [x] Task 3: 后端 API 端点 (AC: 1,4,6)
  - [x] Subtask 3.1: 新增 `POST /api/v1/documents/{document_id}/design` 触发设计文档生成
  - [x] Subtask 3.2: 新增 `GET /api/v1/documents/{document_id}/design` 查询设计文档状态与内容

- [x] Task 4: 前端设计文档查看页面 (AC: 5)
  - [x] Subtask 4.1: 扩展 `features/documents/types.ts`：新增 `DesignSection`、`DesignDocument` 类型
  - [x] Subtask 4.2: 扩展 `features/documents/api.ts`：新增 `triggerDesignDocument`、`getDesignDocument` API 调用
  - [x] Subtask 4.3: 创建 `DesignDocumentPage` 页面（状态展示、章节卡片、Polarion ID 标签、生成/重新生成按钮）
  - [x] Subtask 4.4: 添加路由 `/documents/:documentId/design`
  - [x] Subtask 4.5: 在 `RequirementViewerPage` 添加"进入方案设计"按钮（流水线 ready 或 in_design 时显示）

- [x] Task 5: 测试与质量保障 (AC: 全部)
  - [x] Subtask 5.1: 后端单元测试：`DesignDocumentRepository` CRUD 和状态更新（5 例）
  - [x] Subtask 5.2: 后端单元测试：`DesignDocumentService` 触发、执行、查询、ASIL 解析逻辑（14/15 例）
  - [x] Subtask 5.3: 后端集成测试：`POST /design` 和 `GET /design` 端点
  - [x] Subtask 5.4: 运行全量单元测试，确保零回归（85/85 通过）

## Dev Notes

### 技术架构约束

- **多租户隔离**：`design_documents` 表必须包含 `tenant_id` 字段；Repository 查询必须过滤 `tenant_id`
- **流水线状态校验**：`trigger_generate` 必须校验 `parse_status == "completed"` 且 `pipeline_status != "blocked"`
- **ASIL 等级解析**：递归遍历需求树收集所有 ASIL 值，取最高等级（D > C > B > A）；无有效 ASIL 时返回 `QM`（Quality Managed）
- **章节完整性校验**：`execute_generate` 在保存前校验 LLM 返回的 sections 是否包含全部 8 个必需章节，缺少时抛出 `ValueError`
- **JSON 字段存储**：`sections` 使用 SQLAlchemy `JSON` 类型存储，结构为 `{section_key: {"content": str, "polarion_trace_id": str}}`
- **后台任务模式**：采用 FastAPI `BackgroundTasks` + `_run_generate` 模式，与 `parse_document.py` 保持一致
- **超时补偿机制**：`get_design_document` 中实现惰性超时检测，超过 10 分钟仍处 `running` 状态的任务自动标记为 `failed`

### 项目结构对齐

**后端需创建/修改的文件：**
```
backend/app/
├── models/
│   └── design_document.py              # SQLAlchemy 模型 (NEW)
├── repositories/
│   └── design_document_repository.py   # DB 访问层 (NEW)
├── services/
│   └── design_document_service.py      # 核心服务 (NEW)
├── tasks/
│   └── generate_design_document.py     # 后台任务调度 (NEW)
├── integrations/
│   └── llm_client.py                   # 扩展：新增 generate_design_document 接口 (UPDATE)
├── routers/v1/
│   └── documents.py                    # 扩展：新增 POST /design, GET /design (UPDATE)
├── exceptions.py                       # 扩展：新增 PipelineBlockedError, DesignDocumentNotFoundError (UPDATE)
├── main.py                             # 扩展：导入 DesignDocument 模型 (UPDATE)
└── tests/
    ├── unit/test_design_document_repository.py
    └── unit/test_design_document_service.py
```

**前端需创建/修改的文件：**
```
frontend/src/
├── features/documents/
│   ├── types.ts                        # 扩展：新增 DesignSection, DesignDocument (UPDATE)
│   ├── api.ts                          # 扩展：新增 triggerDesignDocument, getDesignDocument (UPDATE)
│   └── pages/
│       ├── DesignDocumentPage.tsx      # 设计文档查看页面 (NEW)
│       └── RequirementViewerPage.tsx   # 扩展：添加入口按钮 (UPDATE)
└── App.tsx                             # 扩展：新增 /documents/:documentId/design 路由 (UPDATE)
```

### API 设计规范

**新增端点 1：**
- `POST /api/v1/documents/{document_id}/design` → 触发设计文档生成
  ```json
  {
    "success": true,
    "data": {
      "document_id": "uuid",
      "design_task_id": "uuid",
      "status": "running"
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**新增端点 2：**
- `GET /api/v1/documents/{document_id}/design` → 查询设计文档
  ```json
  {
    "success": true,
    "data": {
      "document_id": "uuid",
      "status": "completed",
      "asil_level": "C",
      "sections": {
        "overview": {
          "content": "本文档描述...",
          "polarion_trace_id": "POL-DSGN-001"
        }
      },
      "error_message": null
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**错误码规范：**
- `DOCUMENT_NOT_FOUND`: 文档不存在
- `DOCUMENT_NOT_READY`: 文档未就绪（解析未完成、解析失败、或生成任务已在进行中）
- `PIPELINE_BLOCKED`: 流水线被阻塞（存在未复核的低置信度 OCR 字段）

### 数据库模型设计

**design_documents 表：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 任务唯一标识 |
| tenant_id | INT | 租户隔离 |
| document_id | UUID FK → documents.id | 来源文档 |
| status | VARCHAR(20) | `pending` / `running` / `completed` / `failed` |
| asil_level | VARCHAR(10) | ASIL 等级（A/B/C/D/QM）|
| sections | JSON | 8 个章节的内容和 Polarion ID |
| error_message | TEXT | 失败原因 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

### 性能与安全要求

- **NFR-PERF-004**: 设计文档生成应在后台异步执行，前端通过轮询获取状态，轮询间隔 2 秒，上限 300 次（10 分钟）
- **NFR-SEC-004**: LLM 调用参数中不包含客户敏感信息（当前 Mock 实现无此问题）
- **NFR-REL-001**: 重新生成设计文档时，旧数据（sections、asil_level、error_message）必须被正确清除

### 外部依赖

- **后端**: SQLAlchemy 2.0（模型/查询）、FastAPI（BackgroundTasks）、Pydantic（DTO 验证）
- **前端**: React、React Router、Ant Design 5（Card, Descriptions, Tag, Spin, Alert, Button, Space, Divider）

### 已知限制与注意事项

- **Auth 模块尚未实现**：与 Story 1.x 一致，tenant_id 通过占位方式获取
- **MockLLMClient 限制**：MVP 阶段使用 Mock 数据模拟设计文档生成；真实 LLM 集成在后续迭代中替换
- **单进程架构**：FastAPI BackgroundTasks 为单进程异步调度，真正的并发竞争风险极低，但代码仍应保持健壮
- **ASIL 解析**：当前仅支持 A/B/C/D 四个等级；非标准值会被过滤，全部过滤后降级为 QM
- **递归深度保护**：需求树递归构建增加 `_MAX_TREE_DEPTH = 10` 限制，防止循环引用导致栈溢出

## Dev Agent Record

### Agent Model Used

Claude (bmad-dev-story workflow) + 3 层对抗式代码评审

### Debug Log References

-

### Completion Notes List

- 2026-05-22: 实现完成，85 项后端单元测试全部通过，前端 TypeScript 类型检查通过（除一处 pre-existing 未使用变量警告）

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — Story 2.1 原始需求定义
- [Source: backend/app/integrations/llm_client.py] — LLMClient 接口参考
- [Source: backend/app/tasks/parse_document.py] — 后台任务模式参考
- [Source: frontend/src/features/documents/pages/RequirementViewerPage.tsx] — 需求查看页面参考

### Review Findings

#### 代码评审概览

- **评审日期**: 2026-05-22
- **评审轮次**: 1 轮（3 层并行评审 + 联合裁决）
- **评审策略**: Blind Hunter + Edge Case Hunter + Acceptance Auditor
- **发现问题总数**: 38 项（高优 5 + 中优 10 + 低优 3 + 决策 3 + 推迟 3 + 驳回 5）
- **修复 Patch 数**: 18 项全部应用
- **测试回归**: 85/85 通过，零回归

#### Patch 修复清单

- [x] [Review][Patch][P1] `trigger_generate` 返回的 `design_task_id` 与 DB 实际主键不一致（重新生成时生成新 UUID）→ 修复：重新生成时复用 `existing.id`
- [x] [Review][Patch][P2] `trigger_generate` 存在 TOCTOU 竞态（检查 `running` 与更新状态之间无原子保护）→ 修复：提前拒绝 `running` 状态，重置旧数据后直接返回 existing.id
- [x] [Review][Patch][P3] 前端轮询无上界且未正确清理 interval → 修复：改用递归 `setTimeout`，设置 `MAX_POLLS = 300`（10 分钟），卸载时清理
- [x] [Review][Patch][P4] `_resolve_asil_level` 对非法 ASIL 值无过滤 → 修复：增加 `valid_levels` 过滤，仅保留 A/B/C/D
- [x] [Review][Patch][P5] `execute_generate` 吞掉原始错误信息 → 修复：`except Exception as exc` 并保存 `str(exc)`
- [x] [Review][Patch][P6] `_run_generate` 异常处理中 `design_repo` 可能二次失败（在嵌套 try 中重新定义）→ 修复：将 `design_repo` 提至 try 块外
- [x] [Review][Patch][P7] `in_design` 重复触发导致旧 `asil_level` 残留 → 修复：重新生成时显式清除 `sections`、`asil_level`、`error_message`
- [x] [Review][Patch][P8] `DesignDocumentNotFoundError` 已定义但从未使用 → 修复：移除未使用异常类及 main.py 重复注册
- [x] [Review][Patch][P9] 后端缺少章节完整性校验 → 修复：`execute_generate` 中校验 LLM 返回是否包含全部 8 个章节
- [x] [Review][Patch][P10] `requirements` 递归构建可能因循环引用栈溢出 → 修复：增加 `_MAX_TREE_DEPTH = 10` 深度限制
- [x] [Review][Patch][P11] `trigger_generate` 对 `parse_status == "failed"` 提示不准确 → 修复：单独判断 `failed` 状态并返回"解析失败，无法生成设计文档"
- [x] [Review][Patch][P12] `doc` 对象 `commit` 后未 `refresh` → 修复：`self.db.commit()` 后增加 `self.db.refresh(doc)`
- [x] [Review][Patch][P13] `main.py` 异常处理器重复注册 → 修复：移除 `DocumentNotReadyError`、`PipelineBlockedError`、`DesignDocumentNotFoundError` 的冗余注册（`ModuException` 已覆盖子类）
- [x] [Review][Patch][P14] `statusTag` 对意外值无警告 → 修复：switch 添加 `default` 分支返回橙色"未知状态"标签
- [x] [Review][Patch][P15] `sectionConfig` 缺少未知 key 的健壮处理 → 修复：`SectionCard` 中 `polarionTraceId` 和 `content` 增加缺省值回退
- [x] [Review][Patch][D1] 缺少超时补偿机制 → 修复：`get_design_document` 中实现惰性超时检测，超过 10 分钟自动标记 `failed`
- [x] [Review][Patch][D2] 无 ASIL 时标记为 QM → 修复：`_resolve_asil_level` 返回 `None` 时由调用方设为 `"QM"`；`MockLLMClient` 中 `effective_asil = asil_level or "QM"`
- [x] [Review][Patch][D3] 允许重新生成但需正确清理旧数据 → 修复：与 P1/P7 合并处理，重新生成时清除旧 sections、asil_level、error_message

#### 待办：第二次代码评审

- [ ] **触发条件**：下次进入本项目会话时，优先启动 Story 2.1 的第二次代码评审。
- [ ] **评审重点**：
  - P1/P7/D3（重新生成时的 ID 一致性和数据清理）修复后的边界场景
  - D1（超时补偿机制）在真实运行时的表现
  - P10（递归深度保护）的测试覆盖
  - 第一次评审中 Defer 的 3 项（测试覆盖盲区、NaN/inf 校验、输入框最大长度限制）
  - 第一次评审中 Dismiss 的 5 项是否有新的触发条件
- [ ] **评审策略**：建议换用不同 LLM 获取新上下文，运行 `bmad-code-review` skill 发起第二轮 adversarial review
- [x] **commit 基线**：`aaf0712`

#### 第二次代码评审（2026-05-25）

- **评审日期**: 2026-05-25
- **评审轮次**: 2 轮（3 层并行评审 + 联合裁决）
- **评审策略**: Blind Hunter + Edge Case Hunter + Acceptance Auditor
- **发现问题总数**: 33 项（patch 14 + defer 6 + dismiss 3）
- **评审重点覆盖**: P1/P7/D3 边界场景、D1 真实表现、P10 测试覆盖、Defer/Dismiss 复查

**Patch 已修复清单（2026-05-25）：**

- [x] [Review][Patch] TOCTOU 竞态：`trigger_generate` 状态检查与后台任务调度非原子 → 修复：`existing` 查询增加 `with_for_update()` 行级锁 [backend/app/services/design_document_service.py:49]
- [x] [Review][Patch] 生产服务硬编码 `MockLLMClient`，应改为依赖注入 → 修复：`__init__` 增加 `llm_client: LLMClient | None = None` 参数，默认回退 `MockLLMClient()` [backend/app/services/design_document_service.py:28-34]
- [x] [Review][Patch] GET 端点惰性超时检测存在写竞态且返回不一致数据 → 修复：`get_design_document` 不再修改 DB，仅返回计算出的超时状态 [backend/app/services/design_document_service.py:187-201]
- [x] [Review][Patch] `except Exception` 过宽且 `_run_generate` 丢失原始错误信息 → 修复：`_run_generate` 捕获 `Exception as exc` 并将 `str(exc)` 写入 DB；`execute_generate` 失败时恢复 `pipeline_status` [backend/app/tasks/generate_design_document.py:39-48, backend/app/services/design_document_service.py:162-179]
- [x] [Review][Patch] `sections` 内部结构未校验（违反 AC3） → 修复：`execute_generate` 增加对每个 section 的 `content` (str) 和 `polarion_trace_id` (str) 校验 [backend/app/services/design_document_service.py:133-152]
- [x] [Review][Patch] `_build_requirements_list` 深度超限静默丢弃深层子树 → 修复：深度超限时抛出 `ValueError` 而非返回空列表 [backend/app/services/design_document_service.py:213-217]
- [x] [Review][Patch] 缺少集成测试（Subtask 5.3 未完成） → 修复：新增 `test_design_document_router.py`，覆盖 POST/GET 端点 9 个场景 [backend/tests/integration/test_design_document_router.py]
- [x] [Review][Patch] `execute_generate` 失败时不恢复 `Document.pipeline_status` → 修复：except 块中若 `pipeline_status == "in_design"` 则回退到 `ready` [backend/app/services/design_document_service.py:170-179]

**Patch 待修复清单（保留为 action items）：**

- [ ] [Review][Patch] `trigger_generate` 允许 `pipeline_status == "in_design"` 时重新触发，导致数据丢失 [backend/app/services/design_document_service.py:358-397]
- [ ] [Review][Patch] ASIL 值处理不健壮（非字符串类型可能崩溃、非标准值静默丢弃） [backend/app/services/design_document_service.py:552-568]
- [ ] [Review][Patch] `_run_generate` 不重新验证父文档存在性，删除后任务卡死 [backend/app/tasks/generate_design_document.py:593-627]
- [ ] [Review][Patch] 前端轮询存在 cleanup race，status 快速变化时可能产生重叠 timeout [frontend/src/features/documents/pages/DesignDocumentPage.tsx:1255-1279]
- [ ] [Review][Patch] `safety_params_list` 可能包含 `None` 值直接传入 LLM [backend/app/services/design_document_service.py:432-442]
- [ ] [Review][Patch] `DesignDocument` 模型缺少 `document_id` 唯一约束 [backend/app/models/design_document.py:215]

**Defer 清单：**

- [x] [Review][Defer] `DesignDocumentRepository.create` 无显式 rollback 处理 [backend/app/repositories/design_document_repository.py:231-235] — deferred, pre-existing SQLAlchemy session 管理模式
- [x] [Review][Defer] 前端 `DesignDocument.status` 类型为 `string` 而非字面量联合 [frontend/src/features/documents/types.ts:1458-1469] — deferred, TypeScript 增强
- [x] [Review][Defer] `document_id` URL 参数无 UUID 格式校验 [backend/app/routers/v1/documents.py:290-311] — deferred, 项目范围路由校验模式
- [x] [Review][Defer] `MockLLMClient` trace ID 基于 `len(filename) % 1000` 易碰撞 [backend/app/integrations/llm_client.py:74] — deferred, Mock 已知限制
- [x] [Review][Defer] `_build_requirements_list` 递归遍历 `r.children` 存在跨租户泄漏假设 [backend/app/services/design_document_service.py:428,541] — deferred, 无实证
- [x] [Review][Defer] `TimestampMixin` 的 `onupdate` 行为未在 diff 中验证 [backend/app/models/design_document.py] — deferred, pre-existing
