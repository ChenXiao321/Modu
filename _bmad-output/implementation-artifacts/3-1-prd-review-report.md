# Story 3.1 PRD Adversarial Review Report

**Reviewer**: Claude (adversarial mode)
**Date**: 2026-06-01
**PRD**: `3-1-misra-compliant-code-auto-generation.md`
**Status**: 4 项 P0/P1 问题已修复，3 项 P2 改进建议已采纳
**修复日期**: 2026-06-01
**测试基线**: 167 passed, 0 failed

---

## P0 — 阻塞性问题（必须修复）

### P0-1: `_update_pipeline_block_status` 终态保护缺失

**位置**: PRD Subtask 4.3 + `document_parse_service.py:400-424`

**问题**:
现有 `_update_pipeline_block_status` 只保护 `in_design` 状态：

```python
if doc.pipeline_status == "in_design":
    return
```

如果 OCR 字段确认后重新触发解析（或未来有人调用此函数），`design_reviewed` 和 `code_generated` 都会被覆盖为 `ready`/`blocked`。

**风险**: 代码生成完成后，用户若重新触发文档解析（例如重新上传芯片手册），`_update_pipeline_block_status` 会把 `code_generated` 状态刷回 `ready`，导致用户误以为可以重新触发代码生成（实际上旧代码文件还在数据库里）。

**修复建议**:
```python
_PROTECTED_STATUSES = {"in_design", "design_reviewed", "code_generated"}
if doc.pipeline_status in _PROTECTED_STATUSES:
    return
```

**PRD 应更新**:
- Subtask 4.3 明确要求："将 `_update_pipeline_block_status` 的硬编码终态保护改为集合 `_PROTECTED_STATUSES`，包含 `in_design`, `design_reviewed`, `code_generated`"

---

### P0-2: `DesignDocumentService.trigger_generate` 错误地将 `design_reviewed` 视为锁定

**位置**: PRD AC1 + `design_document_service.py:69-70`

**问题**:
现有代码：

```python
if doc.pipeline_status == "design_reviewed":
    raise DesignReviewLockedError(document_id)
```

PRD AC1 要求：`pipeline_status == "design_reviewed"` 是**触发代码生成的前置条件**。

但现有 `trigger_generate` 是用于**设计文档生成**的（Epic 2），不是用于代码生成的。PRD 中的 `CodeGenerationService.trigger_generate` 是新的服务，不会调用 `DesignDocumentService.trigger_generate`。

**风险**: 如果开发者误以为 `CodeGenerationService` 可以复用 `DesignDocumentService` 的触发逻辑，会引入严重 bug。两个服务的触发条件完全相反。

**修复建议**:
PRD 应在 Dev Notes 中明确加一条：
> **服务隔离**: `CodeGenerationService` 必须独立实现 `trigger_generate`，不可复用 `DesignDocumentService.trigger_generate`。后者的 `design_reviewed` 锁定逻辑仅适用于设计文档重新生成场景。

---

## P1 — 高风险问题（建议修复）

### P1-1: MockLLMClient step_type 检测不可靠

**位置**: PRD AC6 + `llm_client.py:184-281`

**问题**:
`MockLLMClient._call` 通过 prompt 内容的关键词匹配来推断 step_type：

```python
if "fc_architecture" in prompt:
    step_type = "design_detail"
elif "fc_list" in prompt:
    step_type = "design_fc"
# ...
else:
    return "{}"  # 空 JSON，会导致 parse_output 失败
```

PRD 的代码生成 Agent 使用了新的 prompt 模板（`code_01_module_analysis.j2`、`code_02_code_generation.j2`），如果模板中没有包含上述任何关键词，Mock 会返回 `{}`，导致 `parse_output` 抛出 `LLMOutputFormatError`。

**风险**: 本地测试（使用 MockLLMClient）时，代码生成步骤会直接失败，开发者无法在无 LLM API 的环境下验证代码生成流程。

**修复建议**:
1. PRD 明确要求 prompt 模板包含 Mock 检测关键词（如 `module_analysis`、`code_generation`、`file_path` 等）
2. 或在 `MockLLMClient._call` 中新增代码生成分支：

```python
elif "module_analysis" in prompt or "模块架构" in prompt:
    step_type = "code_module"
elif "code_generation" in prompt or "代码生成" in prompt:
    step_type = "code_source"
```

3. 新增 `agent_code_module_mock.j2` 和 `agent_code_source_mock.j2` 模板

**PRD 应更新**:
- Subtask 2.5 增加："Mock 输出通过 Jinja2 模板渲染，需在 `llm_client.py` 的 `_call` 方法中新增 `code_module` / `code_source` 分支检测"

---

### P1-2: Agent 输入源组织未明确

**位置**: PRD AC2 + `workflow.py:26-34`

**问题**:
`WorkflowContext` 只有一个 `document_text: str` 字段。代码生成需要两个输入源：
- `DesignDocument.sections`（legacy 格式，8 个章节的 JSON）
- `SoftwareDetailedDesign`（新格式，fc_architecture + detailed_design + safety_design）

PRD 说"基于 `DesignDocument.sections` 和 `SoftwareDetailedDesign`"，但没有说明如何组织这两个输入。

**风险**: 开发者可能只传递 `DesignDocument.sections`（因为 `WorkflowContext.document_text` 语义上是"文档文本"），而忽略了 `SoftwareDetailedDesign` 中的结构化设计信息，导致代码生成质量差。

**修复建议**:
PRD 应在 Dev Notes 中明确：
> **Agent 输入构造**: `CodeGenerationService.execute_generate` 需将 `SoftwareDetailedDesign` 的 `fc_architecture` 和 `detailed_design` 字段序列化为 JSON 字符串，作为 `WorkflowContext.document_text` 传递。`DesignDocument.sections` 中的 `overview` 和 `interface_definition` 可作为辅助上下文附加在 `document_text` 末尾。

或者更好的方案：扩展 `WorkflowContext` 新增 `design_data: dict` 字段（非破坏式，默认值 `None`）。

---

### P1-3: `GeneratedCodeFile` 缺少重新生成策略

**位置**: PRD Subtask 1.2

**问题**:
PRD 中 `GeneratedCodeFileRepository` 有 `delete_by_document`，但没有说明：
1. 重新生成时是否删除旧文件？
2. 如果删除，何时删除（触发时还是成功后）？
3. 是否支持并发触发保护（类似 `DesignDocumentService` 的 `status == "running"` 检查）？

**风险**: 用户快速双击"生成代码"按钮，可能产生两组代码文件（旧 + 新），或第二个请求在第一个的 `delete` + `commit` 之间插入，导致数据不一致。

**修复建议**:
PRD 应增加：
> **重新生成策略**: `CodeGenerationService.trigger_generate` 需校验：
> 1. `pipeline_status == "design_reviewed"`（前置条件）
> 2. 如果 `Document.pipeline_status == "code_generation_running"`，抛出 `DocumentNotReadyError`（防止并发）
> 3. 如果已有 `GeneratedCodeFile` 记录，在触发时立即 `delete_by_document` + `commit`，然后更新 `pipeline_status` 为 `code_generation_running`

---

## P2 — 改进建议（可选）

### P2-1: AC2 输入源优先级歧义

PRD AC2 说"基于 `DesignDocument.sections` 和 `SoftwareDetailedDesign`"，但：
- `DesignDocument.sections` 是 legacy 兼容格式（`interface_definition` 内容是 JSON 字符串）
- `SoftwareDetailedDesign.detailed_design` 是结构化 Agent 输出（函数签名、数据类型、状态机等）

**建议**: 明确主次关系 — 代码生成应以 `SoftwareDetailedDesign` 为主输入，`DesignDocument.sections` 仅作补充（如提取模块概述文本）。Prompt 模板中应体现这一优先级。

---

### P2-2: 文件命名规则未定义

PRD 使用 `src/MyModule.h` 作为示例，但未说明：
- `MyModule` 如何从设计文档推导？（project_number？fc_architecture 中的模块名？）
- 多个 FC 模块是否生成多个文件？（如 `src/WdgM.h` + `src/WdgM.c` + `src/EcuM.h` + `src/EcuM.c`）

**建议**: 在 AC3 或 Dev Notes 中补充命名规则：文件名从 `fc_architecture.fc_modules[].module_name` 推导，蛇形命名法，路径前缀固定为 `src/`。

---

### P2-3: JSON 中多行代码 content 的合法性风险

Step 2 的 LLM 输出格式：
```json
{"files": [{"file_path": "src/main.c", "content": "#include <stdio.h>\nint main() {\n    return 0;\n}"}]}
```

LLM 可能在 JSON 字符串中直接插入未转义的换行符（这在 JSON 中不合法），或在 markdown code block 中返回代码。`_clean_json_response` 已经处理了 markdown fence，但未处理 JSON 字符串中的未转义换行符。

**建议**: 在 Prompt 模板中明确约束："所有代码内容必须放在 JSON 字符串的 `content` 字段中，换行符使用 `\n` 转义，禁止在 JSON 字符串内直接换行"。

---

## 统计

| 级别 | 数量 | 状态 |
|------|------|------|
| P0 | 2 | 必须修复 |
| P1 | 3 | 建议修复 |
| P2 | 3 | 可选改进 |

---

## 修复后下一步

修复以上 P0/P1 问题后，PRD 即可进入实现阶段。推荐修复顺序：
1. P0-1（`_update_pipeline_block_status` 终态保护）
2. P0-2（服务隔离说明）
3. P1-1（Mock step_type 检测）
4. P1-2（Agent 输入源组织）
5. P1-3（重新生成策略）
