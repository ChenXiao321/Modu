# Story 2.2: 设计文档分屏审查与在线修正

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 嵌入式软件工程师,
I want 在 Web 界面上逐节审查 AI 生成的设计文档并在线修正,
so that 我可以对设计细节进行人工把关，确保方案符合实际需求。

## Acceptance Criteria

1. [AC1] 给定设计文档已生成（status == "completed"），当工程师进入设计审查界面时，界面支持分屏显示：左侧展示原始需求文档（功能需求树 + 安全关键参数），右侧展示 AI 生成的设计文档 8 个章节。
2. [AC2] 当工程师在右侧对任意章节点击"编辑"时，该章节进入可编辑状态（多行文本框），修改完成后点击"保存修订"，系统将原始内容和修改后内容保存为修订记录。
3. [AC3] 当工程师点击"查看修订历史"时，系统展示该章节的所有修订记录列表，每条记录包含作者、时间戳、修改前后差异（diff 视图），并支持一键回退到任意历史版本。
4. [AC4] 当工程师在任意章节点击"添加评审意见"时，可输入逐条评审意见并保存，评审意见按章节聚合展示，支持标记为"已解决"。
5. [AC5] 当存在未解决的评审意见时，设计文档状态栏显示警告提示；所有评审意见解决后，工程师可点击"提交设计审查"，将流水线状态推进到 `design_reviewed`，允许进入 Story 2.3 的设计校验节点。
6. [AC6] 若设计文档尚未生成（status != "completed"），审查界面显示引导提示，引导工程师先生成设计文档。

## Tasks / Subtasks

- [x] Task 1: 后端数据模型与存储层 (AC: 2,3,4)
  - [x] Subtask 1.1: 新建 `DesignRevision` SQLAlchemy 模型（字段：id, tenant_id, design_document_id, document_id, section_key, author, original_content, revised_content, created_at）
  - [x] Subtask 1.2: 新建 `ReviewComment` SQLAlchemy 模型（字段：id, tenant_id, design_document_id, document_id, section_key, author, comment_text, created_at, resolved_at, resolved_by）
  - [x] Subtask 1.3: 新建 `DesignRevisionRepository`（create, list_by_section, get_latest_by_section）
  - [x] Subtask 1.4: 新建 `ReviewCommentRepository`（create, list_by_section, resolve）
  - [x] Subtask 1.5: 在 `main.py` 导入新模型以确保建表

- [x] Task 2: 后端设计审查服务 (AC: 1,2,3,4,5,6)
  - [x] Subtask 2.1: 创建 `DesignReviewService`，实现 `get_review_context`（聚合原始需求 + 设计文档 + 修订记录 + 评审意见）
  - [x] Subtask 2.2: 实现 `save_revision`（保存章节修订：校验设计文档存在且 completed → 读取当前章节 content 作为 original → 写入 revision 记录 → 更新 design_document.sections 中对应章节的 content 为修订后内容）
  - [x] Subtask 2.3: 实现 `get_revision_history`（按章节查询修订记录，含 diff 计算）
  - [x] Subtask 2.4: 实现 `add_review_comment`（添加评审意见）
  - [x] Subtask 2.5: 实现 `resolve_review_comment`（标记评审意见为已解决）
  - [x] Subtask 2.6: 实现 `submit_design_review`（校验所有评审意见已解决 → 更新 Document.pipeline_status 为 `design_reviewed`）
  - [x] Subtask 2.7: 实现 `rollback_to_revision`（将 design_document.sections 中对应章节的 content 回退到指定修订版本）

- [x] Task 3: 后端 API 端点 (AC: 1,2,3,4,5,6)
  - [x] Subtask 3.1: 新增 `GET /api/v1/documents/{document_id}/design-review` → 获取分屏审查完整上下文
  - [x] Subtask 3.2: 新增 `POST /api/v1/documents/{document_id}/design-revisions` → 保存章节修订
  - [x] Subtask 3.3: 新增 `GET /api/v1/documents/{document_id}/design-revisions?section_key={key}` → 查询章节修订历史
  - [x] Subtask 3.4: 新增 `POST /api/v1/documents/{document_id}/review-comments` → 添加评审意见
  - [x] Subtask 3.5: 新增 `GET /api/v1/documents/{document_id}/review-comments?section_key={key}` → 查询评审意见列表
  - [x] Subtask 3.6: 新增 `PATCH /api/v1/documents/{document_id}/review-comments/{comment_id}/resolve` → 标记评审意见已解决
  - [x] Subtask 3.7: 新增 `POST /api/v1/documents/{document_id}/design-review/submit` → 提交设计审查
  - [x] Subtask 3.8: 新增 `POST /api/v1/documents/{document_id}/design-revisions/{revision_id}/rollback` → 回退到指定修订版本

- [x] Task 4: 前端分屏审查页面 (AC: 1,2,3,4,5,6)
  - [x] Subtask 4.1: 扩展 `features/documents/types.ts`：新增 `DesignRevision`、`ReviewComment`、`DesignReviewContext` 类型
  - [x] Subtask 4.2: 扩展 `features/documents/api.ts`：新增分屏审查相关 API 调用
  - [x] Subtask 4.3: 创建 `DesignReviewPage.tsx`（分屏审查主页面：左侧需求树 + 安全参数，右侧章节列表 + 编辑/评审能力）
  - [x] Subtask 4.4: 创建 `SectionEditor.tsx`（章节编辑组件：展示模式 ↔ 编辑模式切换，保存/取消按钮）
  - [x] Subtask 4.5: 创建 `RevisionHistory.tsx`（修订历史抽屉/弹窗：列表 + diff 视图 + 回退按钮）
  - [x] Subtask 4.6: 创建 `ReviewCommentPanel.tsx`（评审意见面板：按章节展示，添加输入框，解决按钮）
  - [x] Subtask 4.7: 在 `App.tsx` 添加路由 `/documents/:documentId/design-review`
  - [x] Subtask 4.8: 在 `DesignDocumentPage.tsx` 添加"进入设计审查"按钮（status == "completed" 时显示）

- [x] Task 5: 测试与质量保障 (AC: 全部)
  - [x] Subtask 5.1: 后端单元测试：`DesignRevisionRepository` CRUD（4 例）
  - [x] Subtask 5.2: 后端单元测试：`ReviewCommentRepository` CRUD + resolve（5 例）
  - [x] Subtask 5.3: 后端单元测试：`DesignReviewService` 核心逻辑（12 例）
  - [x] Subtask 5.4: 后端集成测试：分屏审查 API 端点（17 例）
  - [x] Subtask 5.5: 运行全量单元测试，确保零回归（156/156 通过）

### Review Findings (Code Review 2026-05-27)

**decision-needed (3):**
- [x] [Review][Decision] NFR-REL-003: localStorage 仅缓存复核人姓名，未缓存草稿文本 — **决策：1A（现在实现）** → 转为 patch
- [x] [Review][Decision] NFR-PERF-001: `get_review_context` 使用 5 次顺序查询 — **决策：2B（留到性能迭代）** → 转为 defer
- [x] [Review][Decision] RequirementViewerPage 在 `pipeline_status == 'design_reviewed'` 时仍显示"进入方案设计"按钮 — **决策：3A（保持现状）** → dismiss

**patch (19):**
- [x] [Review][Patch] 事务不一致：`save_revision` / `rollback_to_revision` 中 revision_repo.create 已 commit，design update 又在独立 commit 中 [design_review_service.py:801-807, 938-949]
- [x] [Review][Patch] 并发竞争：`submit_design_review` 缺少 `with_for_update()`，并发请求可能同时通过 pending check [design_review_service.py:904-906]
- [x] [Review][Patch] `rollback_to_revision` 的 `author` 通过 query param 传入，与其他端点不一致且绕过 Pydantic 校验 [documents.py:242]
- [x] [Review][Patch] `save_revision` / `rollback_to_revision` 在 section 非 dict 时会将 `polarion_trace_id` 重置为空字符串 [design_review_service.py:805-806, 944-947]
- [x] [Review][Patch] `SaveRevisionRequest` 允许空字符串 `revised_content` [schemas/design_review.py:619]
- [x] [Review][Patch] `DesignReviewContextResponse.design_document` 使用弱类型 `dict` 而非 Pydantic model [schemas/design_review.py:665]
- [x] [Review][Patch] `resolve_review_comment` router 未校验 comment 是否属于传入的 document_id [documents.py:221-222]
- [x] [Review][Patch] `get_review_comments` router 内联构建 response dict，未使用 Pydantic schema [documents.py:198-210]
- [x] [Review][Patch] `design_revision.py` 和 `review_comment.py` 中 `TIMESTAMP` 导入未使用 [models/design_revision.py:3, models/review_comment.py:3]
- [x] [Review][Patch] 集成测试 `client` fixture 在 dependency override 后调用 `drop_all`，顺序危险 [test_design_review_router.py:1055]
- [x] [Review][Patch] `test_design_review_service.py` 缺少 design 为 None 的分支测试
- [x] [Review][Patch] 前端所有 API 函数未检查 `res.data.success`，HTTP 200 但 success=false 时返回 undefined [api.ts:125-201]
- [x] [Review][Patch] `DesignReviewPage` 异步请求未使用 AbortController，组件卸载时可能 setState 到已卸载组件 [DesignReviewPage.tsx:109-113]
- [x] [Review][Patch] `localStorage.getItem/setItem` 未包裹 try/catch（隐私模式/配额超限会抛异常）[DesignReviewPage.tsx:73, 209-212]
- [x] [Review][Patch] 多处 `navigate` 调用未防护 `documentId` 为 undefined 的情况 [DesignReviewPage.tsx:270, 340; DesignDocumentPage.tsx:205; RequirementViewerPage.tsx:247]
- [x] [Review][Patch] `SectionEditor` draft 未同步外部 content prop 变化，可能被静默覆盖 [SectionEditor.tsx:13]
- [x] [Review][Patch] `RevisionHistory` 将 diff 字符串直接渲染到 `<pre>`，未做 HTML 转义 [RevisionHistory.tsx]
- [x] [Review][Patch] `pipelineStatus` 类型为 `string` 而非联合类型 [types.ts]
- [x] [Review][Patch] `ReviewCommentPanel` 使用单一 `loading`/`sending` 状态阻塞所有按钮 [ReviewCommentPanel.tsx:47, 113]
- [x] [Review][Patch][Decision-1A] `SectionEditor` 草稿自动保存到 localStorage（按 documentId + sectionKey 隔离）

**defer (8):**
- [x] [Review][Defer] `DesignRevision` 缺少 `reason`/`change_description` 字段 — 功能增强，deferred
- [x] [Review][Defer] Pydantic schema 缺少 `max_length` 限制 — 待后续统一加固
- [x] [Review][Defer] `author` 字段为自由文本无格式校验 — Auth 模块实现后统一处理
- [x] [Review][Defer] `_compute_diff` 对超大输入无保护 — MVP 边界情况
- [x] [Review][Defer] 缺少 `(document_id, section_key)` 复合索引 — 性能优化 deferred
- [x] [Review][Defer] `_VALID_SECTION_KEYS` 与 `_REQUIRED_SECTIONS` 硬编码重复 — 架构层面后续统一
- [x] [Review][Defer] 前端缺少重试/离线处理 — 功能增强 deferred
- [x] [Review][Defer] 缺少 Error Boundary / 按章节错误隔离 — 架构层面 deferred

### Review Findings Round 2 (Code Review 2026-05-27)

**decision-needed (0):**

**patch (13):**
- [x] [Review][Patch] snake_case/camelCase 前后端字段命名不匹配，导致前端运行时读取 undefined [api.ts, design_review_service.py, types.ts]
- [x] [Review][Patch] `save_revision` 并发竞争：两用户同时保存同一章节，后者无冲突覆盖前者 [design_review_service.py:96]
- [x] [Review][Patch] `submit_design_review` TOCTOU 竞争：pending 检查通过后仍可被插入新评论 [design_review_service.py:212]
- [x] [Review][Patch] `resolve_review_comment` repository 层未过滤 document_id，仅靠 service 层校验 [review_comment_repository.py:61]
- [x] [Review][Patch] `rollback_to_revision` repository 层未过滤 document_id，仅靠 service 层校验 [design_revision_repository.py:48]
- [x] [Review][Patch] `comment_repo.resolve` 自行 commit，破坏 service 层事务边界一致性 [review_comment_repository.py:61]
- [x] [Review][Patch] `_compute_diff` 对 None 输入会抛 AttributeError [design_review_service.py:306]
- [x] [Review][Patch] 修订历史/评论列表按 `created_at.desc()` 排序，时间戳相同时顺序非确定性 [design_revision_repository.py:20, review_comment_repository.py:22]
- [x] [Review][Patch] 重复解决评论无防护，覆盖审计信息 [review_comment_repository.py:61]
- [x] [Review][Patch] `checkSuccess` 未防御 `res.data` 为 undefined 的情况 [api.ts:285]
- [x] [Review][Patch] Pydantic `min_length=1` 不阻止纯空格字符串，需 service 层 `.strip()` 校验 [design_review_service.py, schemas/design_review.py]
- [x] [Review][Patch] `pipelineStatus` 联合类型缺失 `'failed'` / `'generating'` 等 DesignDocument 状态 [types.ts]
- [x] [Review][Patch] `get_review_context` 一次性加载全量评论/需求/安全参数，大文档时存在负载风险 [design_review_service.py:49]

**defer (5):**
- [x] [Review][Defer] 前端大数组未做懒加载/分页（requirements、safetyParameters）— 性能优化 deferred
- [x] [Review][Defer] `submit_design_review` 幂等性未处理（缺少幂等键）— 功能增强 deferred
- [x] [Review][Defer] `author` 字段来源为请求体而非 CurrentUser（Auth 未实现）— 预存模式 deferred
- [x] [Review][Defer] 无输入长度上限（revised_content、comment_text 可超大）— MVP 边界 deferred
- [x] [Review][Defer] 缺少并发竞争场景的集成测试 — 测试增强 deferred

**dismiss (7):**
- [x] [Review][Dismiss] `documentId && navigate` 防御性编码是合理实践
- [x] [Review][Dismiss] `rowHoverStyle` 死代码已清理
- [x] [Review][Dismiss] `get_review_context` design=None 返回 pending 符合 AC6 设计
- [x] [Review][Dismiss] 允许向 design.sections 中不存在的 section_key 添加内容，属于预期扩展行为
- [x] [Review][Dismiss] SQLAlchemy ORM 已参数化查询，SQL 注入风险可控
- [x] [Review][Dismiss] `get_review_context` 字段 null 安全由模型约束保证
- [x] [Review][Dismiss] Diff 文件截断属评审过程产物，已修复

## Dev Notes

### 技术架构约束

- **多租户隔离**：`design_revisions` 和 `review_comments` 表必须包含 `tenant_id` 字段；Repository 查询必须过滤 `tenant_id`
- **设计文档状态校验**：`save_revision` 和 `add_review_comment` 必须校验对应 DesignDocument 的 `status == "completed"`，否则拒绝操作
- **章节 key 白名单**：只接受 2.1 中定义的 8 个标准章节 key（overview, references, system_architecture, interface_definition, dynamic_behavior, resource_consumption, error_handling, test_strategy），非法 key 返回 400
- **作者信息来源**：当前 Auth 模块尚未实现，作者字段暂从 `CurrentUser` 依赖注入获取（fallback 为 `"anonymous"`），与 2.1 保持一致
- **diff 视图**：后端计算 diff，前端展示。使用 Python `difflib.unified_diff` 生成统一格式 diff 字符串，前端使用 `<pre>` 标签展示（MVP 阶段不做语法高亮）
- **修订记录不可删除**：修订记录为审计数据，只允许追加和回退，不允许物理删除（符合 ASPICE 追溯要求）
- **评审意见解决权限**：当前实现中，任何工程师都可解决任何评审意见（RBAC 细化留待后续 Story）
- **流水线状态推进**：`submit_design_review` 将 `Document.pipeline_status` 从 `in_design` 更新为 `design_reviewed`，后续 Story 2.3 的 ReviewGate 将基于此状态做门禁判断

### 项目结构对齐

**后端需创建/修改的文件：**
```
backend/app/
├── models/
│   ├── design_revision.py              # SQLAlchemy 模型 (NEW)
│   ├── review_comment.py               # SQLAlchemy 模型 (NEW)
│   └── __init__.py                     # 扩展：导入新模型 (UPDATE)
├── repositories/
│   ├── design_revision_repository.py   # DB 访问层 (NEW)
│   └── review_comment_repository.py    # DB 访问层 (NEW)
├── services/
│   └── design_review_service.py        # 核心服务 (NEW)
├── routers/v1/
│   └── documents.py                    # 扩展：新增设计审查端点 (UPDATE)
├── schemas/
│   └── design_review.py                # Pydantic DTOs (NEW)
├── main.py                             # 扩展：导入新模型 (UPDATE)
└── tests/
    ├── unit/test_design_revision_repository.py
    ├── unit/test_review_comment_repository.py
    ├── unit/test_design_review_service.py
    └── integration/test_design_review_router.py
```

**前端需创建/修改的文件：**
```
frontend/src/
├── features/documents/
│   ├── types.ts                        # 扩展：新增 DesignRevision, ReviewComment, DesignReviewContext (UPDATE)
│   ├── api.ts                          # 扩展：新增设计审查 API (UPDATE)
│   └── pages/
│       ├── DesignReviewPage.tsx        # 分屏审查主页面 (NEW)
│       ├── DesignDocumentPage.tsx      # 扩展：添加"进入设计审查"入口 (UPDATE)
│       └── RequirementViewerPage.tsx   # 扩展：添加"进入设计审查"入口（当 pipeline_status == in_design 时）(UPDATE)
│   └── components/
│       ├── SectionEditor.tsx           # 章节编辑器 (NEW)
│       ├── RevisionHistory.tsx         # 修订历史抽屉 (NEW)
│       └── ReviewCommentPanel.tsx      # 评审意见面板 (NEW)
└── App.tsx                             # 扩展：新增 /documents/:documentId/design-review 路由 (UPDATE)
```

### API 设计规范

**新增端点 1：**
- `GET /api/v1/documents/{document_id}/design-review` → 获取分屏审查完整上下文
  ```json
  {
    "success": true,
    "data": {
      "document_id": "uuid",
      "design_document": {
        "status": "completed",
        "asil_level": "C",
        "sections": { ... }
      },
      "requirements": [ ... ],
      "safety_parameters": [ ... ],
      "review_comments": {
        "overview": [ { "id": "uuid", "author": "张三", "comment_text": "...", "created_at": "...", "resolved_at": null } ]
      },
      "pending_comments_count": 3,
      "pipeline_status": "in_design"
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**新增端点 2：**
- `POST /api/v1/documents/{document_id}/design-revisions` → 保存章节修订
  Request:
  ```json
  { "section_key": "overview", "revised_content": "修改后的内容...", "author": "张三" }
  ```
  Response:
  ```json
  {
    "success": true,
    "data": {
      "revision_id": "uuid",
      "section_key": "overview",
      "original_content": "原始内容...",
      "revised_content": "修改后的内容...",
      "author": "张三",
      "created_at": "2026-05-25T10:00:00+08:00"
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**新增端点 3：**
- `GET /api/v1/documents/{document_id}/design-revisions?section_key=overview` → 查询修订历史
  Response:
  ```json
  {
    "success": true,
    "data": {
      "section_key": "overview",
      "revisions": [
        {
          "id": "uuid",
          "author": "张三",
          "original_content": "...",
          "revised_content": "...",
          "diff": "--- original\n+++ revised\n@@ -1,3 +1,3 @@...",
          "created_at": "2026-05-25T10:00:00+08:00"
        }
      ]
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**新增端点 4：**
- `POST /api/v1/documents/{document_id}/review-comments` → 添加评审意见
  Request:
  ```json
  { "section_key": "overview", "comment_text": "建议补充时序图", "author": "张三" }
  ```

**新增端点 5：**
- `PATCH /api/v1/documents/{document_id}/review-comments/{comment_id}/resolve` → 解决评审意见
  Request:
  ```json
  { "resolved_by": "李四" }
  ```

**新增端点 6：**
- `POST /api/v1/documents/{document_id}/design-review/submit` → 提交设计审查
  Response:
  ```json
  {
    "success": true,
    "data": {
      "document_id": "uuid",
      "pipeline_status": "design_reviewed",
      "submitted_at": "2026-05-25T10:00:00+08:00"
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**错误码规范：**
- `DESIGN_DOCUMENT_NOT_FOUND`: 设计文档不存在
- `DESIGN_DOCUMENT_NOT_READY`: 设计文档尚未生成完成
- `INVALID_SECTION_KEY`: 章节 key 不在白名单中
- `REVISION_NOT_FOUND`: 指定的修订记录不存在
- `COMMENT_NOT_FOUND`: 指定的评审意见不存在
- `PENDING_COMMENTS_EXIST`: 提交审查时仍存在未解决的评审意见
- `PIPELINE_STATUS_INVALID`: 当前流水线状态不允许执行此操作

### 数据库模型设计

**design_revisions 表：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 修订记录唯一标识 |
| tenant_id | INT | 租户隔离 |
| design_document_id | UUID FK → design_documents.id | 关联设计文档 |
| document_id | UUID FK → documents.id | 关联原始文档（冗余，便于查询） |
| section_key | VARCHAR(50) | 章节 key |
| author | VARCHAR(100) | 修订作者 |
| original_content | TEXT | 修订前的内容 |
| revised_content | TEXT | 修订后的内容 |
| created_at | TIMESTAMPTZ | 创建时间 |

**review_comments 表：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 评审意见唯一标识 |
| tenant_id | INT | 租户隔离 |
| design_document_id | UUID FK → design_documents.id | 关联设计文档 |
| document_id | UUID FK → documents.id | 关联原始文档 |
| section_key | VARCHAR(50) | 章节 key |
| author | VARCHAR(100) | 提出人 |
| comment_text | TEXT | 评审意见内容 |
| created_at | TIMESTAMPTZ | 创建时间 |
| resolved_at | TIMESTAMPTZ | 解决时间（NULL 表示未解决） |
| resolved_by | VARCHAR(100) | 解决人 |

### 性能与安全要求

- **NFR-REL-003**: 表单输入（评审意见、修订内容）在意外刷新或浏览器崩溃后不丢失。前端需实现本地自动保存（localStorage 缓存输入中的文本，提交成功后清除）
- **NFR-SEC-002**: 敏感文档原文不在前端浏览器持久存储。分屏左侧仅展示结构化需求树（RequirementTreeNode）和安全参数（SafetyParameter），不展示原始 PDF/Word 内容
- **NFR-PERF-001**: 分屏审查页面首次加载时间 ≤ 3 秒。`get_review_context` 需通过 JOIN 或并行查询优化，避免 N+1
- **审计要求**: 所有修订记录和评审意见永久保留（≥ 7 年），与 2.3 的评审记录锁定机制数据互通

### 外部依赖

- **后端**: SQLAlchemy 2.0（模型/查询）、FastAPI（API 路由）、Pydantic（DTO 验证）、difflib（diff 计算）
- **前端**: React、React Router、Ant Design 5（Splitter 分屏组件、Drawer 抽屉、Input.TextArea、Timeline、Comment 组件）

### 已知限制与注意事项

- **Auth 模块尚未实现**：与 Story 1.x/2.1 一致，author / resolved_by 字段通过 `CurrentUser` 占位获取
- **Diff 语法高亮**：MVP 阶段使用 `<pre>` 标签展示纯文本 diff，后续迭代可引入 `react-diff-viewer` 等库
- **回退操作记录**：`rollback_to_revision` 本身也会生成一条新的 revision 记录（original = 当前内容，revised = 回退目标内容），保证操作可追溯
- **并发编辑**：MVP 阶段不做乐观锁或实时协作冲突处理；后保存的修订覆盖前者，但两者都作为 revision 记录保留
- **前端状态管理**：`DesignReviewPage` 使用本地 useState 管理编辑状态，不做全局 Zustand store（页面级状态足够）
- **与 2.3 的衔接**：`submit_design_review` 将 `pipeline_status` 推进到 `design_reviewed`，Story 2.3 的 ReviewGate 将基于此状态判断是否允许进入代码生成阶段

## Dev Agent Record

### Agent Model Used

Claude (bmad-dev-story workflow)

### Debug Log References

-

### Completion Notes List

- 2026-05-26: Story 2.2 实现完成，所有 AC 满足，全量测试 156/156 通过零回归。
  - 后端：新增 DesignRevision / ReviewComment 模型与 Repository，DesignReviewService 实现 7 个核心方法，8 个 API 端点全部接入。
  - 前端：DesignReviewPage 分屏布局（Splitter），SectionEditor / RevisionHistory / ReviewCommentPanel 组件，localStorage 持久化复核人姓名。
  - 测试：DesignRevisionRepository 4 例、ReviewCommentRepository 5 例、DesignReviewService 12 例、集成测试 17 例。
- 2026-05-27: Round 2 代码评审 13 项 patch 全部修复，全量测试 157/157 通过零回归。
  - 后端：修复 snake_case/camelCase 映射、并发行锁、TOCTOU 重查、仓库层 document_id 过滤、事务边界统一、None 安全 diff、确定性排序、重复解决防护、空白内容校验、查询上限保护。
  - 前端：修复 checkSuccess undefined 防御、api.ts 全量字段映射、PipelineStatus 联合类型扩充。
  - 测试：更新 ReviewCommentRepository 单元测试以匹配新 resolve 签名。

### File List

- `backend/app/exceptions.py` (UPDATE)
- `backend/app/models/design_revision.py`
- `backend/app/models/review_comment.py`
- `backend/app/repositories/design_revision_repository.py`
- `backend/app/repositories/review_comment_repository.py`
- `backend/app/services/design_review_service.py`
- `backend/app/routers/v1/documents.py` (UPDATE)
- `backend/app/schemas/design_review.py`
- `backend/app/main.py` (UPDATE)
- `backend/tests/unit/test_design_revision_repository.py`
- `backend/tests/unit/test_review_comment_repository.py`
- `backend/tests/unit/test_design_review_service.py`
- `backend/tests/integration/test_design_review_router.py`
- `frontend/src/features/documents/types.ts` (UPDATE)
- `frontend/src/features/documents/api.ts` (UPDATE)
- `frontend/src/features/documents/pages/DesignReviewPage.tsx`
- `frontend/src/features/documents/pages/DesignDocumentPage.tsx` (UPDATE)
- `frontend/src/features/documents/pages/RequirementViewerPage.tsx` (UPDATE)
- `frontend/src/features/documents/components/SectionEditor.tsx`
- `frontend/src/features/documents/components/RevisionHistory.tsx`
- `frontend/src/features/documents/components/ReviewCommentPanel.tsx`
- `frontend/src/App.tsx` (UPDATE)

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2] — Story 2.2 原始需求定义
- [Source: _bmad-output/planning-artifacts/architecture.md] — 项目架构、技术栈、命名规范
- [Source: _bmad-output/planning-artifacts/prd.md#REQ-2] — FR-REQ-006 需求详情
- [Source: _bmad-output/implementation-artifacts/2-1-design-document-auto-generation.md] — Story 2.1 实现记录、数据模型、API 规范
- [Source: backend/app/models/design_document.py] — DesignDocument 模型参考
- [Source: backend/app/repositories/design_document_repository.py] — Repository 模式参考
- [Source: backend/app/services/design_document_service.py] — Service 层模式参考
- [Source: backend/app/routers/v1/documents.py] — 路由注册模式参考
- [Source: frontend/src/features/documents/pages/DesignDocumentPage.tsx] — 前端页面模式参考
- [Source: frontend/src/features/documents/pages/RequirementViewerPage.tsx] — 需求树展示组件复用参考
- [Source: backend/app/exceptions.py] — 异常类规范参考
- [Source: backend/app/schemas/documents.py] — Pydantic DTO 规范参考
