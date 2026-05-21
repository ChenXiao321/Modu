# Story 1.3: 安全关键参数识别与可追溯注册

Status: ready-for-dev

## Story

As a 嵌入式软件工程师,
I want 平台自动识别文档中的安全关键参数并注册为独立可追溯条目,
so that 时序、电压阈值、温度范围、看门狗周期等安全参数不会被遗漏。

## Acceptance Criteria

1. [AC1] 给定文档解析结果中存在安全关键参数（时序、电压阈值、温度范围、看门狗周期、超时时间等），当平台执行安全关键参数识别时，每个参数以 `SW-REQ-SAF-xxx` 编号独立标识，不嵌入功能描述段落。
2. [AC2] 每个安全关键参数条目包含：参数名、数值、单位、容差、来源文档页码/章节。
3. [AC3] 安全关键参数条目与普通功能需求条目在界面上分区展示（如使用独立标签页或独立面板）。
4. [AC4] 安全关键参数与原始文档之间具备追溯关系，可通过参数条目查看其来源文档和章节。
5. [AC5] 若文档中未识别到安全关键参数，界面应明确提示"未检测到安全关键参数"而非空白展示。

## Tasks / Subtasks

- [ ] Task 1: 后端数据模型与存储层扩展 (AC: 1,2,4)
  - [ ] Subtask 1.1: 新建 `SafetyCriticalParameter` SQLAlchemy 模型（字段：id, tenant_id, document_id, parameter_id, name, value, unit, tolerance, chapter, source_page, created_at, updated_at）
  - [ ] Subtask 1.2: 新建 `SafetyParameterRepository`（create, get_by_document, delete_by_document）
  - [ ] Subtask 1.3: 新建 Alembic 迁移脚本，添加 `safety_critical_parameters` 表
  - [ ] Subtask 1.4: 在 `ParsedRequirement` 模型中保持现状（安全参数不混入需求树）

- [ ] Task 2: 后端安全关键参数识别服务 (AC: 1,2,4)
  - [ ] Subtask 2.1: 扩展 `LLMClient` 抽象接口，新增 `extract_safety_parameters(document_text, filename) -> list[dict]` 方法
  - [ ] Subtask 2.2: 在 `MockLLMClient` 中实现安全参数模拟提取（返回时序、电压、温度、看门狗等示例参数）
  - [ ] Subtask 2.3: 扩展 `DocumentParseService.execute_parse`，在需求提取后调用安全参数识别，并持久化到 `safety_critical_parameters` 表
  - [ ] Subtask 2.4: 新增 `DocumentParseService.get_safety_parameters(tenant_id, document_id) -> list[dict]` 方法
  - [ ] Subtask 2.5: 新增 `GET /api/v1/documents/{document_id}/safety-parameters` 端点
  - [ ] Subtask 2.6: 扩展 `ParseStatusResponse` 或文档状态以包含 `safety_parameter_count`（可选，用于前端空状态提示）

- [ ] Task 3: 前端安全关键参数分区展示 (AC: 3,5)
  - [ ] Subtask 3.1: 扩展 `RequirementTreeNode` 类型或新增 `SafetyParameter` 类型（字段：id, parameterId, name, value, unit, tolerance, chapter, sourcePage）
  - [ ] Subtask 3.2: 在 `features/documents/api.ts` 中新增 `getSafetyParameters(documentId)` API 调用函数
  - [ ] Subtask 3.3: 创建 `SafetyParameterTable` 组件（Ant Design Table，展示参数名、数值、单位、容差、来源章节）
  - [ ] Subtask 3.4: 修改 `RequirementViewerPage`，使用 Tabs 组件分区展示："功能需求"（现有 RequirementTree）和 "安全关键参数"（新建 SafetyParameterTable）
  - [ ] Subtask 3.5: 当安全参数列表为空时展示友好提示（AC5）
  - [ ] Subtask 3.6: 在路由或文档列表中添加入口，使工程师可进入需求查看页面

- [ ] Task 4: 测试与质量保障 (AC: 全部)
  - [ ] Subtask 4.1: 后端单元测试：`SafetyParameterRepository` CRUD 操作
  - [ ] Subtask 4.2: 后端单元测试：`DocumentParseService` 中安全参数提取和持久化逻辑
  - [ ] Subtask 4.3: 后端集成测试：`GET /documents/{id}/safety-parameters` 端点响应格式和权限隔离
  - [ ] Subtask 4.4: 前端组件测试：`SafetyParameterTable` 渲染、空状态、数据展示
  - [ ] Subtask 4.5: 前端类型测试：确保前后端字段命名映射正确（snake_case ↔ camelCase）

## Dev Notes

### 技术架构约束

- **多租户隔离**：`safety_critical_parameters` 表必须包含 `tenant_id` 字段；Repository 查询必须过滤 `tenant_id`
- **数据边界**：安全关键参数独立于 `parsed_requirements`，不混入需求树结构，以支持独立的分区展示和后续追溯矩阵引用
- **参数编号规则**：`SW-REQ-SAF-{序号:03d}`，序号按文档内识别顺序递增；若已有参数，重新解析时清空旧数据再写入
- **LLM 接口扩展**：当前 `LLMClient` 仅定义 `extract_requirements`；本 Story 需新增 `extract_safety_parameters` 以保持关注点分离
- **解析流程顺序**：`execute_parse` 中先执行文本提取 → 功能需求提取 → 安全参数提取 → 分别持久化 → 更新文档状态为 completed

### 项目结构对齐

**后端需创建/修改的文件：**
```
backend/app/
├── models/
│   └── safety_critical_parameter.py      # SQLAlchemy 模型 (NEW)
├── repositories/
│   └── safety_parameter_repository.py    # DB 访问层 (NEW)
├── schemas/
│   └── requirements.py                   # 扩展：新增 SafetyParameterResponse 等 DTOs (UPDATE)
├── services/
│   └── document_parse_service.py         # 扩展：execute_parse 新增安全参数提取和查询 (UPDATE)
├── integrations/
│   └── llm_client.py                     # 扩展：新增 extract_safety_parameters 接口 (UPDATE)
├── routers/v1/
│   └── documents.py                      # 扩展：新增 GET /safety-parameters 端点 (UPDATE)
└── tests/
    ├── unit/test_safety_parameter_repository.py
    ├── unit/test_document_parse_service_safety.py
    └── integration/test_safety_parameters.py
```

**前端需创建/修改的文件：**
```
frontend/src/
├── features/documents/
│   ├── types.ts                          # 扩展：新增 SafetyParameter 类型 (UPDATE)
│   ├── api.ts                            # 扩展：新增 getSafetyParameters (UPDATE)
│   ├── components/
│   │   ├── RequirementTree.tsx           # 保持现状（或微调样式）
│   │   └── SafetyParameterTable.tsx      # 安全参数表格组件 (NEW)
│   └── pages/
│       └── RequirementViewerPage.tsx     # 扩展：Tabs 分区展示 (UPDATE)
└── tests/
    └── features/documents/
        └── SafetyParameterTable.test.tsx
```

### API 设计规范

**新增端点：**
- `GET /api/v1/documents/{document_id}/safety-parameters` → 标准响应包装
  ```json
  {
    "success": true,
    "data": {
      "document_id": "uuid",
      "parameters": [
        {
          "id": "uuid",
          "parameter_id": "SW-REQ-SAF-001",
          "name": "供电电压阈值",
          "value": "4.5",
          "unit": "V",
          "tolerance": "±0.1",
          "chapter": "3.2.1",
          "source_page": 42
        }
      ]
    },
    "error": null,
    "trace_id": "uuid"
  }
  ```

**错误码规范：**
- `DOCUMENT_NOT_FOUND`: 文档不存在
- `PARSE_NOT_COMPLETED`: 文档尚未完成解析，无法查询安全参数

### 数据库模型设计

**safety_critical_parameters 表：**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | 参数唯一标识 |
| tenant_id | INT | 租户隔离 |
| document_id | UUID FK → documents.id | 来源文档 |
| parameter_id | VARCHAR(50) | `SW-REQ-SAF-xxx` 编号 |
| name | VARCHAR(255) | 参数名（中文或英文） |
| value | VARCHAR(100) | 参数数值 |
| unit | VARCHAR(50) | 单位（V, ms, °C 等） |
| tolerance | VARCHAR(100) | 容差/精度 |
| chapter | VARCHAR(100) | 来源章节 |
| source_page | INT | 来源页码（可选） |
| created_at | TIMESTAMPTZ | 创建时间 |
| updated_at | TIMESTAMPTZ | 更新时间 |

### 性能与安全要求

- **NFR-PERF-003**: AI 分析（含安全参数识别）应在 60 秒内完成（单文档 ≤ 50 页）
- **NFR-SEC-002**: 安全参数属于结构化数据，可在前端展示；原始文档二进制不得在前端持久存储
- 安全参数查询应使用与 `get_requirements_tree` 相同的数据库索引策略（`document_id` + `tenant_id` 复合条件）

### 外部依赖

- **后端**: SQLAlchemy 2.0（模型/查询）、Pydantic（DTO 验证）
- **前端**: Ant Design（Table, Tabs, Tag, Empty 组件）、TanStack Query（数据获取和缓存）

### 已知限制与注意事项

- **Auth 模块尚未实现**：与 Story 1.1/1.2 一致，tenant_id 通过 `dependencies.py` 中的 `get_current_tenant` 占位获取（当前 fallback 到租户 1）
- **MockLLMClient 限制**：MVP 阶段使用 Mock 数据模拟安全参数；真实 LLM 集成在后续迭代中通过 `LLMClient` 替换实现
- **Alembic 迁移**：如果本地数据库已存在 Story 1.1/1.2 的表，需正确生成新的 migration 脚本并执行 `alembic upgrade head`
- **前端路由**：Story 1.2 已创建 `RequirementViewerPage`；本 Story 在其基础上扩展 Tabs 分区，不改动路由结构

### 实现顺序建议

1. 完成后端 `SafetyCriticalParameter` 模型 + Repository + 迁移脚本
2. 扩展 `LLMClient` 和 `MockLLMClient` 的安全参数提取方法
3. 扩展 `DocumentParseService` 的解析流程，持久化安全参数
4. 新增 `GET /safety-parameters` API 端点
5. 扩展前端类型和 API 调用
6. 创建 `SafetyParameterTable` 组件并集成到 `RequirementViewerPage`
7. 编写前后端测试并确保全部通过

## Dev Agent Record

### Agent Model Used

Claude (bmad-dev-story workflow)

### Debug Log References

-

### Completion Notes List

- 2026-05-21: 后端 `SafetyCriticalParameter` 模型创建（含 tenant_id、parameter_id SW-REQ-SAF-xxx 编号规则）
- 2026-05-21: `SafetyParameterRepository` 实现（CRUD + 租户隔离 + 按 parameter_id 排序）
- 2026-05-21: 扩展 `LLMClient` 抽象接口，新增 `extract_safety_parameters` 方法
- 2026-05-21: `MockLLMClient` 实现安全参数模拟提取（电压、温度、看门狗、超时等示例）
- 2026-05-21: `DocumentParseService` 扩展：解析流程新增安全参数提取和持久化，支持清空旧数据后重新写入
- 2026-05-21: 新增 `GET /api/v1/documents/{document_id}/safety-parameters` API 端点
- 2026-05-21: 后端 10 项测试全部通过（4 项 Repository 单元测试 + 4 项 Service 单元测试 + 2 项集成测试）
- 2026-05-21: 前端 `SafetyParameter` 类型定义和 `getSafetyParameters` API 封装
- 2026-05-21: `SafetyParameterTable` 组件实现（Ant Design Table，展示参数名、数值、单位、容差、来源章节/页码）
- 2026-05-21: `RequirementViewerPage` 扩展为 Tabs 分区展示（功能需求 / 安全关键参数）
- 2026-05-21: 前端 3 项组件测试全部通过（空状态、数据展示、缺失字段处理）
- 2026-05-21: 全量后端回归测试 40 项全部通过，无回归
- 2026-05-21: 前端生产构建通过（npm run build success）

## Senior Developer Review (AI)

- **Review Date:** 2026-05-21
- **Review Outcome:** Approved after fixes
- **Total Findings:** 8 (2 High / 4 Medium / 2 Low)
- **Fixed in this session:** 6 (2 High + 4 Medium 全部修复；2 Low 记录为技术债务)

### Action Items

**[x] High — 已修复**
- [x] H-1: `source_page` 字段缺少类型安全转换 → `_persist_safety_parameters` 中增加 `int(source_page)` 转换，无效时回退为 `None`
- [x] H-2: `value` 的零值误判 → 将 `if not param_id or not name or value is None` 改为 `if param_id is None or name is None or value is None`，并增加空字符串校验

**[x] Medium — 已修复**
- [x] M-1: `get_safety_parameters` 未校验文档存在性 → 添加 `doc_repo.get_by_id` 检查，不存在时抛出 `DocumentNotFoundError`
- [x] M-2: 安全参数提取失败导致整个解析任务失败 → 将 `extract_safety_parameters` 包裹在独立 try/except 中，记录 warning 但不阻塞解析
- [x] M-3: `MockLLMClient` 总是返回至少 1 个参数 → 移除 `max(1, ...)`，改为 `text_length % 4`
- [x] M-4: `SafetyCriticalParameter` 缺少反向 relationship → 添加 `document = relationship("Document", backref="safety_parameters")`

**[x] 第二轮修复（2026-05-21）**
- [x] H-1（第二轮）: `extract_safety_parameters` 返回 `None` 导致崩溃 → 增加 `if raw_parameters is not None` 检查
- [x] M-1（第二轮）: `MockLLMClient` 空文档仍返回 1 个参数 → 修正为 `text_length % 4`
- [x] M-2（第二轮）: 重新解析时安全参数提取失败导致数据丢失 → 将 `delete_by_document` 移至成功提取之后
- [x] M-3（第二轮）: `get_safety_parameters` 未检查解析状态 → 增加 `parse_status` 过滤（仅 `completed`/`running` 返回数据）

**[ ] Low — 记录为技术债务**
- [ ] L-1: Table Column render 参数命名不一致（`value` 替代 `text`）
- [ ] L-2: `RequirementViewerPage` 并行请求失败时全部阻断（建议使用 `Promise.allSettled`）

### File List

- backend/app/models/safety_critical_parameter.py
- backend/app/repositories/safety_parameter_repository.py
- backend/app/schemas/requirements.py
- backend/app/integrations/llm_client.py
- backend/app/services/document_parse_service.py
- backend/app/routers/v1/documents.py
- backend/tests/unit/test_safety_parameter_repository.py
- backend/tests/unit/test_document_parse_service_safety.py
- backend/tests/integration/test_safety_parameters.py
- frontend/src/features/documents/types.ts
- frontend/src/features/documents/api.ts
- frontend/src/features/documents/components/SafetyParameterTable.tsx
- frontend/src/features/documents/pages/RequirementViewerPage.tsx
- frontend/tests/features/documents/SafetyParameterTable.test.tsx

## References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1] — Story 1.3 原始需求定义
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture] — 多租户隔离与数据库命名规范
- [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns] — 表名/列名/模型类命名规范
- [Source: backend/app/models/parsed_requirement.py] — Story 1.2 需求模型参考
- [Source: backend/app/integrations/llm_client.py] — Story 1.2 LLMClient 接口参考
- [Source: frontend/src/features/documents/components/RequirementTree.tsx] — Story 1.2 需求树组件参考
