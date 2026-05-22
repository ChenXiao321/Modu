# Story 1.4: OCR 置信度评分与低置信度阻断

Status: done

## Story

As a 嵌入式软件工程师,
I want 平台对扫描件或图片格式文档的 OCR 结果输出置信度评分,
so that 我可以对低置信度提取结果进行人工复核，避免错误数据流入下游代码生成。

## Acceptance Criteria

1. [AC1] 给定上传文档为扫描件或图片格式（JPG/PNG/TIFF/PDF 扫描件），当平台执行 OCR 提取和数值字段识别时，每个提取的数值字段附带置信度分数（0.0–1.0）。
2. [AC2] 置信度 < 0.95 的数值字段自动标记为"需人工复核"。
3. [AC3] 存在未复核的低置信度字段时，流水线自动阻塞，不允许进入方案设计阶段（Epic 2）。
4. [AC4] 工程师在界面对低置信度字段签名确认后，阻塞解除，流水线状态恢复为 ready。
5. [AC5] 非扫描件/图片格式文档（原生文本 PDF/Word/Excel/TXT/PPT）不产生 OCR 置信度评分，流水线默认为 ready。

## Tasks / Subtasks

- [ ] Task 1: 后端数据模型与存储层扩展 (AC: 1,2,3,4,5)
  - [ ] Subtask 1.1: 新建 `OcrExtractionResult` SQLAlchemy 模型（字段：id, tenant_id, document_id, field_id, extracted_text, normalized_value, confidence, field_type, source_page, review_status, reviewed_by, reviewed_at, created_at, updated_at）
  - [ ] Subtask 1.2: 新建 `OcrResultRepository`（create, get_by_document, get_low_confidence_count, update_review_status, delete_by_document）
  - [ ] Subtask 1.3: 扩展 `Document` 模型：新增 `pipeline_status`（blocked / ready / in_design）、`block_reason` 字段
  - [ ] Subtask 1.4: 新建 Alembic 迁移脚本，添加 `ocr_extraction_results` 表及 document 表新列

- [ ] Task 2: 后端 OCR 置信度评分服务 (AC: 1,2,5)
  - [ ] Subtask 2.1: 扩展 `LLMClient` 抽象接口，新增 `extract_ocr_fields(document_text, filename) -> list[dict]` 方法（返回字段含 confidence）
  - [ ] Subtask 2.2: 在 `MockLLMClient` 中实现 OCR 字段模拟提取（确定性置信度，扫描件格式返回低置信度字段）
  - [ ] Subtask 2.3: 扩展 `DocumentParseService.execute_parse`，在解析流程末尾调用 OCR 字段提取（仅对扫描件/图片格式）
  - [ ] Subtask 2.4: 实现 `_persist_ocr_results` 和 `_update_pipeline_block_status`（低置信度未复核 → blocked）
  - [ ] Subtask 2.5: 新增 `DocumentParseService.get_ocr_results(tenant_id, document_id)` 方法
  - [ ] Subtask 2.6: 新增 `DocumentParseService.confirm_low_confidence_field(tenant_id, document_id, field_id, reviewer)` 方法

- [ ] Task 3: 后端 API 端点 (AC: 1,2,3,4)
  - [ ] Subtask 3.1: 新增 `GET /api/v1/documents/{document_id}/ocr-results` 端点
  - [ ] Subtask 3.2: 新增 `POST /api/v1/documents/{document_id}/ocr-fields/{field_id}/confirm` 端点
  - [ ] Subtask 3.3: 扩展 `GET /api/v1/documents/{document_id}/status` 或 `parse/status` 返回 `pipeline_status` 和 `block_reason`

- [ ] Task 4: 前端 OCR 结果展示与复核界面 (AC: 1,2,3,4)
  - [ ] Subtask 4.1: 扩展 `features/documents/types.ts`：新增 `OcrField`、`OcrResultListResponse`、`PipelineStatus` 类型
  - [ ] Subtask 4.2: 扩展 `features/documents/api.ts`：新增 `getOcrResults`、`confirmOcrField` API 调用
  - [ ] Subtask 4.3: 创建 `OcrResultTable` 组件（Ant Design Table，展示提取文本、归一化值、置信度、复核状态；低置信度行红色高亮）
  - [ ] Subtask 4.4: 修改 `RequirementViewerPage`，新增 "OCR 提取结果" Tab，集成 `OcrResultTable`
  - [ ] Subtask 4.5: 在 `RequirementViewerPage` 顶部展示流水线阻塞状态 Alert（blocked 时显示红色警告和阻塞原因）
  - [ ] Subtask 4.6: 在 `OcrResultTable` 中为低置信度未复核字段提供"确认"按钮，调用 confirm API 并刷新数据

- [ ] Task 5: 测试与质量保障 (AC: 全部)
  - [ ] Subtask 5.1: 后端单元测试：`OcrResultRepository` CRUD 和复核状态更新
  - [ ] Subtask 5.2: 后端单元测试：`DocumentParseService` OCR 提取、持久化和阻塞逻辑
  - [ ] Subtask 5.3: 后端集成测试：`GET /ocr-results` 和 `POST /confirm` 端点
  - [ ] Subtask 5.4: 前端组件测试：`OcrResultTable` 渲染、低置信度高亮、确认按钮交互
  - [ ] Subtask 5.5: 端到端场景测试：扫描件解析 → 低置信度字段 → 流水线阻塞 → 人工确认 → 阻塞解除

## Dev Notes

### 技术架构约束

- **多租户隔离**：`ocr_extraction_results` 表必须包含 `tenant_id` 字段；Repository 查询必须过滤 `tenant_id`
- **扫描件检测**：通过 `file_type` 和 `original_filename` 后缀判断是否为扫描件/图片格式。扫描件/图片格式包括：`.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`，以及 file_type 为 `application/pdf` 的文档（PDF 扫描件）。原生文本格式（Word/Excel/TXT/PPT）跳过 OCR 评分。
- **流水线阻塞状态**：`Document.pipeline_status` 枚举值：`ready`（可进入设计）、`blocked`（低置信度未复核）、`in_design`（已进入方案设计）。阻塞解除后恢复为 `ready`。
- **字段编号规则**：`OCR-FIELD-{序号:04d}`，序号按文档内识别顺序递增；重新解析时清空旧数据再写入
- **LLM 接口扩展**：当前 `LLMClient` 已有 `extract_requirements` 和 `extract_safety_parameters`；本 Story 需新增 `extract_ocr_fields`
- **解析流程顺序**：`execute_parse` 中先执行文本提取 → 功能需求提取 → 安全参数提取 → OCR 字段提取（仅扫描件/图片）→ 分别持久化 → 更新流水线阻塞状态 → 更新文档状态为 completed

### 项目结构对齐

**后端需创建/修改的文件：**
```
backend/app/
├── models/
│   ├── document.py                         # 扩展：新增 pipeline_status, block_reason (UPDATE)
│   └── ocr_extraction_result.py            # SQLAlchemy 模型 (NEW)
├── repositories/
│   └── ocr_result_repository.py            # DB 访问层 (NEW)
├── schemas/
│   └── requirements.py                     # 扩展：新增 OcrFieldItem, OcrResultListResponse, ConfirmFieldRequest (UPDATE)
├── services/
│   └── document_parse_service.py           # 扩展：OCR 提取、持久化、阻塞状态管理 (UPDATE)
├── integrations/
│   └── llm_client.py                       # 扩展：新增 extract_ocr_fields 接口 (UPDATE)
├── routers/v1/
│   └── documents.py                        # 扩展：新增 GET /ocr-results, POST /confirm 端点 (UPDATE)
└── tests/
    ├── unit/test_ocr_result_repository.py
    ├── unit/test_document_parse_service_ocr.py
    └── integration/test_ocr_results.py
```

**前端需创建/修改的文件：**
```
frontend/src/
├── features/documents/
│   ├── types.ts                            # 扩展：新增 OcrField, PipelineStatus 类型 (UPDATE)
│   ├── api.ts                              # 扩展：新增 getOcrResults, confirmOcrField (UPDATE)
│   ├── components/
│   │   └── OcrResultTable.tsx              # OCR 结果表格组件 (NEW)
│   └── pages/
│       └── RequirementViewerPage.tsx       # 扩展：新增 OCR Tab 和阻塞状态 Alert (UPDATE)
└── tests/
    └── features/documents/
        └── OcrResultTable.test.tsx
```

### API 设计规范

**新增端点 1：**
- `GET /api/v1/documents/{document_id}/ocr-results` → 标准响应包装
  ```json
  {
    "success": true,
    "data": {
      "document_id": "uuid",
      "pipeline_status": "blocked",
      "block_reason": "存在 3 个低置信度 OCR 字段未复核",
      "fields": [
        {
          "id": "uuid",
          "field_id": "OCR-FIELD-0001",
          "extracted_text": "4.5V ±0.l",
          "normalized_value": "4.5",
          "confidence": 0.72,
          "field_type": "voltage",
          "source_page": 42,
          "review_status": "pending",
          "reviewed_by": null,
          "reviewed_at": null
        }
      ]
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**新增端点 2：**
- `POST /api/v1/documents/{document_id}/ocr-fields/{field_id}/confirm` → Body: `{ "reviewer_name": "张三" }`
  ```json
  {
    "success": true,
    "data": {
      "field_id": "OCR-FIELD-0001",
      "review_status": "confirmed",
      "reviewed_by": "张三",
      "reviewed_at": "2026-05-21T14:30:00+08:00",
      "pipeline_status": "ready",
      "all_confirmed": true
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**扩展端点：**
- `GET /api/v1/documents/{document_id}/parse/status` 响应新增字段：
  ```json
  {
    "document_id": "uuid",
    "status": "completed",
    "progress_percent": 100,
    "message": null,
    "pipeline_status": "blocked",
    "block_reason": "存在 2 个低置信度 OCR 字段未复核"
  }
  ```

**错误码规范：**
- `DOCUMENT_NOT_FOUND`: 文档不存在
- `PARSE_NOT_COMPLETED`: 文档尚未完成解析
- `FIELD_NOT_FOUND`: OCR 字段不存在
- `FIELD_ALREADY_CONFIRMED`: 字段已被确认，不能重复确认
- `PIPELINE_NOT_BLOCKED`: 流水线未阻塞，无需确认

### 数据库模型设计

**ocr_extraction_results 表：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 字段唯一标识 |
| tenant_id | INT | 租户隔离 |
| document_id | UUID FK → documents.id | 来源文档 |
| field_id | VARCHAR(50) | `OCR-FIELD-xxxx` 编号 |
| extracted_text | TEXT | OCR 原始提取文本 |
| normalized_value | VARCHAR(255) | 归一化后的数值 |
| confidence | FLOAT | 置信度分数 0.0–1.0 |
| field_type | VARCHAR(50) | 字段类型（voltage/temperature/timing/etc）|
| source_page | INT | 来源页码 |
| review_status | VARCHAR(20) | `pending` / `confirmed` |
| reviewed_by | VARCHAR(100) | 复核人姓名/签名 |
| reviewed_at | TIMESTAMPTZ | 复核时间 |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

**documents 表扩展：**
| 字段 | 类型 | 说明 |
|------|------|------|
| pipeline_status | VARCHAR(20) | `ready` / `blocked` / `in_design` |
| block_reason | VARCHAR(255) | 阻塞原因描述 |

### 性能与安全要求

- **NFR-PERF-003**: OCR 字段提取应在整体 60 秒内完成（单文档 ≤ 50 页）
- **NFR-SEC-002**: OCR 原始提取文本属于结构化数据，可在前端展示；原始图片二进制不得在前端持久存储
- **NFR-SEC-003**: AI API 调用参数中不包含客户敏感信息（当前 Mock 实现无此问题）

### 外部依赖

- **后端**: SQLAlchemy 2.0（模型/查询）、Pydantic（DTO 验证）
- **前端**: Ant Design（Table, Tabs, Tag, Alert, Button, Empty 组件）

### 已知限制与注意事项

- **Auth 模块尚未实现**：与 Story 1.1/1.2/1.3 一致，tenant_id 和 reviewer 通过占位方式获取
- **MockLLMClient 限制**：MVP 阶段使用 Mock 数据模拟 OCR 字段提取；真实 LLM/OCR 集成在后续迭代中替换
- **PDF 扫描件检测**：当前仅通过 file_type == `application/pdf` 判断；真实场景可能需要内容分析（如检测是否全为图片）
- **Alembic 迁移**：如果本地数据库已存在 Story 1.1/1.2/1.3 的表，需正确生成新的 migration 脚本并执行 `alembic upgrade head`
- **流水线状态流转**：`blocked` → 全部确认 → `ready`；`ready` → 进入设计 → `in_design`；`in_design` 不可逆（由 Epic 2 控制）

### 实现顺序建议

1. 完成后端 `OcrExtractionResult` 模型 + `Document` 扩展 + Repository + 迁移脚本
2. 扩展 `LLMClient` 和 `MockLLMClient` 的 OCR 字段提取方法
3. 扩展 `DocumentParseService` 的解析流程，添加 OCR 提取和流水线阻塞状态更新
4. 新增 `GET /ocr-results` 和 `POST /confirm` API 端点
5. 扩展前端类型和 API 调用
6. 创建 `OcrResultTable` 组件并集成到 `RequirementViewerPage`
7. 添加流水线阻塞状态展示和确认交互
8. 编写前后端测试并确保全部通过

## Dev Agent Record

### Agent Model Used

Claude (bmad-dev-story workflow)

### Debug Log References

-

### Completion Notes List

-

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1] — Story 1.4 原始需求定义
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — 多租户隔离与数据库命名规范
- [Source: backend/app/models/document.py] — Story 1.1 Document 模型参考
- [Source: backend/app/integrations/llm_client.py] — Story 1.2/1.3 LLMClient 接口参考
- [Source: backend/app/services/document_parse_service.py] — Story 1.2/1.3 解析服务参考
- [Source: frontend/src/features/documents/pages/RequirementViewerPage.tsx] — Story 1.3 需求查看页面参考

### Review Findings

#### Patch

- [x] [Review][Patch] `_persist_ocr_results` 未按 spec 强制字段编号规则 `OCR-FIELD-{序号:04d}`，改为服务层强制生成 [document_parse_service.py:937]（决策：1A）
- [x] [Review][Patch] `_is_ocr_document` 对 `application/pdf` 判定过于宽泛，改为界面上让用户手动标记"是否为扫描件" [document_parse_service.py:927]（决策：2C）

- [x] [Review][Patch] `execute_parse` 中 OCR 字段提取异常被静默吞掉，文档仍被标记为 `completed` [document_parse_service.py:897]
- [x] [Review][Patch] `_persist_ocr_results` 循环内逐条 `commit`，无事务包裹，部分失败产生脏数据 [document_parse_service.py:943]
- [x] [Review][Patch] `confirm_low_confidence_field` 存在 TOCTOU 竞态且未校验流水线 `blocked` 状态 [document_parse_service.py:1036]
- [x] [Review][Patch] `get_ocr_results` 在文档重新解析（`running`）或解析失败（`failed`）时返回数据与 `pipeline_status` 可能不一致 [document_parse_service.py:1003]
- [x] [Review][Patch] `DocumentListItem` schema 未同步扩展 `pipeline_status`/`block_reason` [schemas/requirements.py:844]
- [x] [Review][Patch] 前端 `handleConfirmField` 中复核人硬编码为 `'工程师'` [RequirementViewerPage.tsx:1693]
- [x] [Review][Patch] 前端 `getOcrResults`/`confirmOcrField` API 函数缺少 `success` 校验 [api.ts:1431]
- [x] [Review][Patch] `OcrResultTable` 使用全局 `<style>` 标签注入 CSS，存在样式污染风险 [OcrResultTable.tsx:1587]
- [x] [Review][Patch] `OcrResultTable` 的 `rowKey` 依赖后端 `id`，`confirmingFieldId` 状态管理不够健壮 [OcrResultTable.tsx:151,1566]
- [x] [Review][Patch] `test_document_parse_service_ocr.py` 为空文件，缺少 `DocumentParseService` OCR 逻辑的单元测试 [test_document_parse_service_ocr.py]
- [x] [Review][Patch] `test_pipeline_unblocked_after_all_confirmed` 中 `while True` 在 Mock 不返回低置信度字段时可能无限循环 [test_ocr_results.py:159]
- [x] [Review][Patch] `MockLLMClient.extract_ocr_fields` 使用 `text_length % 5` 决定返回字段数，测试不稳定 [llm_client.py:571]
- [x] [Review][Patch] `update_review_status` 在方法内部局部导入 `datetime`，且无乐观锁/原子更新 [ocr_result_repository.py:721]
- [x] [Review][Patch] `delete_by_document` 使用 `synchronize_session=False`，高并发下可能残留旧数据 [ocr_result_repository.py:76]
- [x] [Review][Patch] `_update_pipeline_block_status` 对已进入 `in_design` 的 OCR 文档重新解析时可能错误重置状态 [document_parse_service.py:322]
- [x] [Review][Patch] `ConfirmFieldRequest` 的 `reviewer_name` 无长度和空值校验 [schemas/requirements.py:67]
- [x] [Review][Patch] `get_low_confidence_count` 的 `threshold` 参数未校验 `NaN` 或负值 [ocr_result_repository.py:30]
- [x] [Review][Patch] `OcrExtractionResult` 导入未使用的 `UUID` 类型 [ocr_extraction_result.py:1]
- [x] [Review][Patch] `RequirementViewerPage` 中 `setBlockReason(undefined)` 未使用后端返回的 `blockReason` [RequirementViewerPage.tsx:1707]
- [x] [Review][Patch] `OcrResultTable` 的 `confidence` sorter 在 `NaN` 时行为未定义 [OcrResultTable.tsx:58]
- [x] [Review][Patch] `PipelineNotBlockedError` 已定义但 `confirm_low_confidence_field` 中未使用，未阻塞流水线时仍可确认 [exceptions.py:518]

#### Verification Review Findings (2026-05-22)

- [x] [Review][Patch] `_persist_ocr_results` 中 `extracted_text` 无长度上限，已添加 `_MAX_EXTRACTED_TEXT_LEN = 10000` [document_parse_service.py:303]
- [x] [Review][Patch] `get_ocr_results` running 状态返回不一致的 `pipeline_status`，已改为单独处理返回 `"running"` [document_parse_service.py:366]
- [x] [Review][Defer] `update_review_status_atomic` 会话同步隐患 — MVP 阶段当前调用模式安全，后续重构时需注意 [ocr_result_repository.py:147]
- [x] [Review][Defer] `_persist_ocr_results` 超大事务风险 — MVP 单文档 ≤ 50 页，暂不构成瓶颈 [document_parse_service.py:291]
- [x] [Review][Defer] `_update_pipeline_block_status` 终态硬编码（仅 `in_design`）— 未来新增终态时需扩展 [document_parse_service.py:336]
- [x] [Review][Patch] `delete_by_document` + `_persist_ocr_results` 非原子性 — 已修复：将删除逻辑移入 `_persist_ocr_results` 内部，delete + insert 在同一事务中提交 [document_parse_service.py:291]
- [x] [Review][Defer] `MockLLMClient` 测试覆盖盲区 — 固定返回 3 个字段时若全部高置信度，核心解阻塞路径未被覆盖 [llm_client.py:571]
- [x] [Review][Defer] `get_low_confidence_count` NaN/inf 校验可进一步完善 [ocr_result_repository.py:106]
- [x] [Review][Defer] reviewerName 输入框无前端最大长度限制 [RequirementViewerPage.tsx:1798]
- [x] [Review][Defer] `OcrResultTable` `onRow` style 对象引用可能导致重渲染 [OcrResultTable.tsx:166]
- [x] [Review][Defer] 测试中断言过于宽泛（`pytest.raises(Exception)`）— 应使用具体异常类型 [test_document_parse_service_ocr.py:568]
- [x] [Review][Defer] `source_page` 类型错误静默吞掉，建议添加日志警告 [document_parse_service.py:315]
