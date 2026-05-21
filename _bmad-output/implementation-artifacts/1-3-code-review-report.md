# Story 1.3 代码评审报告

**评审日期:** 2026-05-21
**评审对象:** Story 1.3 — 安全关键参数识别与可追溯注册
**Diff 范围:** Story 1.3 新增/修改的全部文件
**评审模式:** Full（含 Spec 对照）

---

## 评审概览

| 层级 | 状态 |
|------|------|
| Blind Hunter（纯代码 adversarial review） | 完成 |
| Edge Case Hunter（边界与集成分析） | 完成 |
| Acceptance Auditor（Spec 对照验收） | 完成 |

**发现问题总计:** 8 项（2 High / 4 Medium / 2 Low）

---

## High 级别问题（必须修复）

### [H-1] `source_page` 字段缺少类型安全转换

**位置:** `backend/app/services/document_parse_service.py:542`

**问题描述:** `_persist_safety_parameters` 中 `source_page=raw.get("source_page")` 直接将 LLM 返回的原始值赋给模型。如果 LLM 返回字符串 `"42"`，SQLite 在开发/测试阶段会自动宽容转换，但 PostgreSQL 生产环境会抛出类型错误。

**风险:** 部署到 PostgreSQL 后，含 `source_page` 的安全参数会导致解析任务失败。

**修复建议:**
```python
source_page=raw.get("source_page")
if source_page is not None:
    try:
        source_page = int(source_page)
    except (ValueError, TypeError):
        source_page = None
```

**相关 AC:** AC2, AC4

---

### [H-2] `_persist_safety_parameters` 中 `value` 的零值误判

**位置:** `backend/app/services/document_parse_service.py:526`

**问题描述:** 校验逻辑为 `if not param_id or not name or value is None:`。虽然当前 MockLLMClient 返回字符串 value，但真实 LLM 可能返回数值 `0`，而 `not 0` 为 `True`，会导致合法参数被错误拒绝。

**风险:** 真实 LLM 集成后，数值为 0 的安全参数（如 "0V 基准电压"）会被丢弃。

**修复建议:**
```python
if param_id is None or name is None or value is None:
    raise ValueError("...")
```

或更严格地：
```python
if not str(param_id).strip() or not str(name).strip() or value is None:
    raise ValueError("...")
```

**相关 AC:** AC1, AC2

---

## Medium 级别问题（建议修复）

### [M-1] `get_safety_parameters` API 端点未校验文档存在性

**位置:** `backend/app/routers/v1/documents.py:259-267`

**问题描述:** 当 `document_id` 不存在时，端点返回空列表 `{"parameters": []}` 和 HTTP 200，而不是 404。这与 `get_requirements` 的行为一致，但用户可能误以为文档存在只是没有安全参数。

**修复建议:** 在 Service 层或 Router 层添加文档存在性检查，不存在时抛出 `DocumentNotFoundError`（全局异常处理器会转为 404）。

```python
def get_safety_parameters(self, tenant_id: int, document_id: str) -> list[dict]:
    doc = self.doc_repo.get_by_id(document_id, tenant_id)
    if doc is None:
        raise DocumentNotFoundError(document_id)
    params = self.safety_repo.get_by_document(document_id, tenant_id)
    return [...]
```

**相关 AC:** AC4

---

### [M-2] `execute_parse` 中安全参数提取失败导致整个解析任务失败

**位置:** `backend/app/services/document_parse_service.py:441-442`

**问题描述:** 如果 `llm_client.extract_safety_parameters()` 抛出异常，会落入 `except Exception` 块，导致整个解析任务标记为 `failed`，即使需求提取已经成功。安全参数识别应该是"尽力而为"的增强功能，不应阻塞核心需求提取。

**修复建议:** 将安全参数提取包裹在独立的 try/except 中，失败时记录 warning 但继续完成解析。

```python
try:
    raw_parameters = self.llm_client.extract_safety_parameters(text, doc.original_filename)
    self._persist_safety_parameters(tenant_id, document_id, raw_parameters)
except Exception:
    logger.exception("Safety parameter extraction failed for document %s", document_id)
```

**相关 AC:** AC1（不应因安全参数失败而丢失已提取的需求）

---

### [M-3] `MockLLMClient.extract_safety_parameters` 总是返回至少 1 个参数

**位置:** `backend/app/integrations/llm_client.py:160`

**问题描述:** `count = max(1, ...)` 确保即使对空文档也会返回至少 1 个参数。这与真实场景不符（某些文档确实不含安全关键参数），可能导致前端测试和演示时产生误导。

**修复建议:** 移除 `max(1, ...)`，允许返回空列表。

```python
count = min(len(parameters), (text_length % 4) + 1)
```

**相关 AC:** AC5（空状态的测试依赖于真实返回空列表）

---

### [M-4] `SafetyCriticalParameter` 模型缺少反向 relationship

**位置:** `backend/app/models/safety_critical_parameter.py`

**问题描述:** `ParsedRequirement` 定义了 `document = relationship("Document", backref="requirements")`，但 `SafetyCriticalParameter` 没有定义类似的 relationship。这导致无法通过参数反查其来源文档（如 `param.document`）。

**修复建议:**
```python
document = relationship("Document", backref="safety_parameters")
```

**相关 AC:** AC4（追溯关系）

---

## Low 级别问题（可选优化）

### [L-1] `SafetyParameterTable.tsx` 中数值与单位之间缺少空格

**位置:** `frontend/src/features/documents/components/SafetyParameterTable.tsx:25`

**问题描述:** `value` 和 `unit` 渲染在同一个 `<span>` 中，中间没有空格：`{value}{record.unit && <Tag>{record.unit}</Tag>}`。视觉上 "4.5V" 而非 "4.5 V"。

**修复建议:** 在 value 和 Tag 之间添加一个空格或 margin。

```tsx
<span>
  {value}
  {record.unit && <Tag style={{ marginLeft: 4 }}>{record.unit}</Tag>}
</span>
```

> 注：当前代码已使用 `marginLeft: 4`，实际上已处理。但 Column 定义中的 render 函数参数名为 `value` 和 `record`，而 `value` 在 Ant Design Table 中是 cell value，不是 record——这实际上是正确的 API 用法，但可能导致混淆。

**重新评估：** 实际代码中已使用 `marginLeft: 4`，此问题不存在。改为记录一个更实际的问题：Table column 的 `render` 函数第一个参数名为 `text`（AntD 惯例）但实际是 `value`，命名不一致。

**修正为 [L-1]: Column render 参数命名不一致**

```tsx
render: (value: string, record: SafetyParameter) => ...
```

Ant Design Table 文档中 convention 是 `text, record, index`。使用 `value` 虽不影响功能，但偏离团队惯例。

---

### [L-2] `RequirementViewerPage` 并行请求失败时全部阻断

**位置:** `frontend/src/features/documents/pages/RequirementViewerPage.tsx:651-654`

**问题描述:** `Promise.all([getRequirements(documentId), getSafetyParameters(documentId)])` 意味着任一请求失败都会导致整个页面显示错误。用户可能更希望：即使安全参数 API 失败，也能看到功能需求。

**修复建议:** 使用 `Promise.allSettled` 或分离错误状态。

```tsx
const [reqsResult, paramsResult] = await Promise.allSettled([
  getRequirements(documentId),
  getSafetyParameters(documentId),
])
if (reqsResult.status === 'fulfilled') setRequirements(reqsResult.value)
if (paramsResult.status === 'fulfilled') setSafetyParameters(paramsResult.value)
```

**相关 AC:** AC3（分区展示不应互相阻塞）

---

## Acceptance Auditor — Spec 对照结果

| AC | 状态 | 说明 |
|----|------|------|
| AC1 | PASS | `SW-REQ-SAF-xxx` 独立编号，独立存储，不混入需求树 |
| AC2 | PASS | name/value/unit/tolerance/chapter/source_page 全部覆盖 |
| AC3 | PASS | Tabs 分区展示：功能需求 / 安全关键参数 |
| AC4 | PARTIAL | 展示章节和页码，但无反向 document relationship，缺少跳转到文档的链接 |
| AC5 | PASS | 空列表时显示 "未检测到安全关键参数" |

**AC4 备注:** 当前实现满足 MVP 最低要求（展示章节和页码），但完整的"可追溯"应支持从参数条目导航到来源文档。建议在后续迭代中增强。

---

## 修复状态（2026-05-21）

| 问题 | 状态 | 修复位置 |
|------|------|----------|
| H-1 | 已修复 | `document_parse_service.py:_persist_safety_parameters` — 增加 `int(source_page)` 转换，无效时回退为 `None` |
| H-2 | 已修复 | `document_parse_service.py:_persist_safety_parameters` — `value` 校验改为 `value is None`，并增加空字符串校验 |
| M-1 | 已修复 | `document_parse_service.py:get_safety_parameters` — 添加 `doc_repo.get_by_id` 存在性检查 |
| M-2 | 已修复 | `document_parse_service.py:execute_parse` — `extract_safety_parameters` 包裹独立 try/except |
| M-3 | 已修复 | `llm_client.py:extract_safety_parameters` — 移除 `max(1, ...)` |
| M-4 | 已修复 | `safety_critical_parameter.py` — 添加 `document = relationship(..., backref="safety_parameters")` |
| L-1 | 延后 | 记录为技术债务 |
| L-2 | 延后 | 记录为技术债务 |

**回归测试结果：** 后端 46 项测试全部通过，前端 6 项测试全部通过，生产构建成功。

---

## 回归测试验证项

修复后验证结果：
- [x] `test_persist_safety_parameters_success` 仍通过（source_page 为 int 和 string 的情况）
- [x] 新增测试：`value="0"` 和 `value=0` 的处理
- [x] `test_get_safety_parameters_empty` 仍通过
- [x] 前端 `SafetyParameterTable.test.tsx` 全部通过
- [x] 全量后端 46 项测试通过
