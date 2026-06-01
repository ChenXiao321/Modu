# Story 3.1: MISRA 合规代码自动生成

Status: backlog

## Story

As a 嵌入式软件工程师,
I want 平台在设计审查通过后自动生成符合 MISRA C:2012 规范的 C 语言模块代码,
so that 我可以直接获得可直接集成到 TC38x 基础工程的头文件和源文件，减少手工编码工作量，并确保代码风格统一、编译器适配正确。

## Acceptance Criteria

1. [AC1] 给定设计审查已通过（`pipeline_status == "design_reviewed"`），当用户触发代码生成时，后端异步执行生成任务并返回任务 ID。
2. [AC2] 生成过程调用 LLM，以 `SoftwareDetailedDesign`（`fc_architecture` + `detailed_design`）为主输入、`DesignDocument.sections` 为辅助上下文，产出 MISRA 合规的 C 代码，至少包含 1 个头文件（`.h`）和 1 个源文件（`.c`）。
3. [AC3] 生成的代码遵循平台内置代码生成模板约束：文件头注释格式（ASPICE 追溯标识占位）、命名规范（函数/变量/宏/类型）、模块接口风格（初始化、读写、回调、错误处理）、TC38x 寄存器访问模式与内存映射约定、Tasking 6.3.1 编译器适配语法（`pragma`、`intrinsic`、`__attribute__`）。
4. [AC4] 代码生成完成后，流水线状态自动迁移为 `code_generated`，生成的代码文件可被查询和下载。
5. [AC5] 若设计审查未通过（`pipeline_status != "design_reviewed"`），触发代码生成时返回明确的错误提示，且不允许进入生成阶段。
6. [AC6] `MockLLMClient` 支持确定性代码生成输出，确保单元测试和集成测试可重复运行。

## Tasks / Subtasks

- [ ] Task 1: 后端数据模型与存储层 (AC: 1,2,4)
  - [ ] Subtask 1.1: 新建 `GeneratedCodeFile` SQLAlchemy 模型（字段：`id`, `tenant_id`, `document_id`, `file_path`, `file_type` {"header"|"source"}, `content` Text, `polarion_trace_id` 预留, `asil_level` 预留, `created_at`, `updated_at`）
  - [ ] Subtask 1.2: 新建 `GeneratedCodeFileRepository`（`create`, `get_by_document`, `get_by_id`, `delete_by_document`）
  - [ ] Subtask 1.3: 在 `main.py` 导入 `GeneratedCodeFile` 模型以确保建表

- [ ] Task 2: 后端代码生成 Agent 工作流 (AC: 2,3,6)
  - [ ] Subtask 2.1: 新建 `CodeGenerationStep`（`code_01_module_analysis`），分析设计文档并输出模块架构 JSON（文件清单、接口定义、类型定义、宏定义）
  - [ ] Subtask 2.2: 新建 `CodeGenerationStep`（`code_02_code_generation`），基于模块架构输出完整代码文件内容 JSON（`{"files": [{"file_path": "...", "file_type": "header|source", "content": "..."}]}`）
  - [ ] Subtask 2.3: 新建 `build_code_generation_steps(template_dir)` 工厂函数，返回 2-step 列表
  - [ ] Subtask 2.4: 创建代码生成 Prompt 模板（`code_01_module_analysis.j2`、`code_02_code_generation.j2`），内置 TC38x/Tasking/MISRA/ASPICE 约束
  - [ ] Subtask 2.5: 在 `MockLLMClient._call` 新增 `code_module` / `code_source` 分支检测与硬编码 Mock 输出（至少 1 个 `.h` + 1 个 `.c`，含标准文件头注释和空函数体）；Prompt 模板需包含可被检测的关键词（`module_architecture`、`code_generation` 或 `code_01` / `code_02`）
  - [ ] Subtask 2.6: 新建 `CodeGenerationService`，实现 `trigger_generate`（前置校验）、`execute_generate`（同步 Agent 工作流执行）、`get_code_files`（查询）
  - [ ] Subtask 2.7: 实现流水线状态校验：`pipeline_status == "design_reviewed"` 方可触发，否则抛 `PipelineStatusInvalidError`；若 `pipeline_status == "code_generation_running"` 则抛 `DocumentNotReadyError`（防并发）

- [ ] Task 3: 后端 API 端点 (AC: 1,4,5)
  - [ ] Subtask 3.1: 新增 `POST /api/v1/documents/{document_id}/code-generation` 触发代码生成
  - [ ] Subtask 3.2: 新增 `GET /api/v1/documents/{document_id}/code-files` 查询生成的代码文件列表
  - [ ] Subtask 3.3: 新增 `GET /api/v1/documents/{document_id}/code-files/{file_id}` 查询单个代码文件内容

- [ ] Task 4: 流水线状态扩展 (AC: 1,4,5)
  - [ ] Subtask 4.1: 在 `Document` 模型的 `pipeline_status` 枚举中扩展 `code_generation_running` 和 `code_generated` 状态（向后兼容现有枚举校验）
  - [ ] Subtask 4.2: 在 `submit_design_review` 后允许触发代码生成；`execute_generate` 成功后将 `pipeline_status` 更新为 `code_generated`
  - [ ] Subtask 4.3: 在 `_update_pipeline_block_status` 中确保新状态不破坏现有终态保护逻辑

- [ ] Task 5: 测试与质量保障 (AC: 全部)
  - [ ] Subtask 5.1: 后端单元测试：`GeneratedCodeFileRepository` CRUD（5 例）
  - [ ] Subtask 5.2: 后端单元测试：`CodeGenerationService` 触发校验、执行流程、Mock 输出解析、状态迁移（10 例）
  - [ ] Subtask 5.3: 后端集成测试：`POST /code-generation`、`GET /code-files` 端点（6 例）
  - [ ] Subtask 5.4: 运行全量单元测试，确保零回归

## Dev Notes

### 技术架构约束

- **多租户隔离**：`generated_code_files` 表必须包含 `tenant_id` 字段；Repository 查询必须过滤 `tenant_id`。
- **服务隔离**：`CodeGenerationService` 必须独立实现 `trigger_generate`，不可复用 `DesignDocumentService.trigger_generate`。后者的 `design_reviewed` 锁定逻辑仅适用于设计文档重新生成场景；代码生成的前置条件恰恰是 `pipeline_status == "design_reviewed"`。
- **流水线状态机**：`code_generation_running` 是中间态，`code_generated` 是终态。终态保护逻辑需与 `in_design` / `design_reviewed` 保持一致（进入终态后不允许回退）。`_update_pipeline_block_status` 已扩展 `_PROTECTED_STATUSES = {"in_design", "design_reviewed", "code_generated"}` 保护所有终态。
- **重新生成策略**：`CodeGenerationService.trigger_generate` 需校验：① `pipeline_status == "design_reviewed"`；② 若 `pipeline_status == "code_generation_running"` 则抛 `DocumentNotReadyError`（防并发）；③ 若已有 `GeneratedCodeFile` 记录，在触发时立即 `delete_by_document` + `commit`，然后更新 `pipeline_status` 为 `code_generation_running`。
- **Agent 输入源组织**：`CodeGenerationService.execute_generate` 需将 `SoftwareDetailedDesign` 的 `fc_architecture` 和 `detailed_design` 字段序列化为 JSON 字符串，作为 `WorkflowContext.document_text` 传递；`DesignDocument.sections` 中的 `overview` 和 `interface_definition` 仅作辅助上下文附加在末尾。代码生成以结构化设计数据为主输入，legacy sections 为补充。
- **文件命名规则**：文件名从 `fc_architecture.fc_modules[].module_name` 推导，蛇形命名法（如 `WdgM` → `WdgM.h`/`WdgM.c`），路径前缀固定为 `src/`。若存在多个 FC 模块，为每个模块生成独立的 `.h` + `.c` 文件对。
- **Agent 工作流复用**：直接使用现有 `AgentWorkflowEngine` + `WorkflowContext` + `Step` 抽象，无需新建工作流引擎。`CodeGenerationStep` 继承 `Step`，复用 `build_prompt` / `parse_output` / `run` 机制。
- **Prompt 模板位置**：新建 `backend/app/agent/prompts/code_01_module_analysis.j2` 和 `code_02_code_generation.j2`，与现有 design agent prompts 放在同一目录。
- **LLM 输出格式**：Step 1 输出 JSON（模块架构），Step 2 输出 JSON（文件列表）。`parse_output` 需校验 JSON 结构完整性，缺少 `files` 数组或 `content` 为空时抛出 `LLMOutputFormatError`。
- **Mock 输出约束**：`MockLLMClient` 的代码生成输出必须包含至少一个 `.h` 文件和一个 `.c` 文件，且 `.h` 文件包含 `#ifndef` / `#define` / `#endif` 守卫，`.c` 文件包含对应 `#include`。
- **代码内容存储**：`GeneratedCodeFile.content` 使用 SQLAlchemy `Text` 类型，存储完整文件内容（含换行符）。文件路径使用相对路径（如 `src/MyModule.h`），便于后续与用户基础工程合并。
- **MISRA 合规提示**：Prompt 模板中需明确列出 MISRA C:2012 核心规则（如规则 15.5 单一出口、规则 17.7 返回值必须使用、规则 21.3 禁止动态内存分配等），约束 LLM 输出风格。
- **JSON 字符串合法性约束**：Prompt 模板中必须明确要求 LLM 将代码内容放在 JSON 字符串的 `content` 字段中，换行符使用 `\n` 转义，禁止在 JSON 字符串值内直接换行。`parse_output` 需使用 `json.loads` 严格解析，解析失败时抛出 `LLMOutputFormatError`。
- **Mock 检测关键词**：`code_01_module_analysis.j2` 模板需包含 `module_architecture` 或 `code_01` 关键词；`code_02_code_generation.j2` 模板需包含 `code_generation` 或 `code_02` 关键词，确保 `MockLLMClient._call` 能正确识别 step_type。
- **性能约束**：单模块代码生成目标耗时 ≤ 90 秒（NFR-004），Agent 工作流 2 步各 1 次 LLM 调用，总调用次数 ≤ 2 次。
