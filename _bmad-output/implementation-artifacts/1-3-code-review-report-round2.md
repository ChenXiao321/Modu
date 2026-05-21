# Story 1.3 代码评审报告（第二轮）

**评审日期:** 2026-05-21
**评审对象:** Story 1.3 修复后代码
**评审模式:** Full（含 Spec 对照）

---

## 评审概览

| 层级 | 状态 |
|------|------|
| Blind Hunter（纯代码 adversarial review） | 完成 |
| Edge Case Hunter（边界与集成分析） | 完成 |
| Acceptance Auditor（Spec 对照验收） | 完成 |

**发现问题总计:** 5 项（1 High / 3 Medium / 1 Low）

**第一轮修复质量:** 6 项修复中，5 项完全正确，1 项（M-3）修复不完全。

---

## High 级别问题（必须修复）

### [H-1] `extract_safety_parameters` 返回 `None` 时 `_persist_safety_parameters` 会崩溃

**位置:** `backend/app/services/document_parse_service.py:86`

**问题描述:** `_persist_safety_parameters` 直接对 `raw_parameters` 进行 `for raw in raw_parameters` 迭代。如果真实 LLM 集成时 `extract_safety_parameters` 返回 `None`（而非空列表），会抛出 `TypeError: 'NoneType' object is not iterable`。

**风险:** 解析任务失败，需求提取成功但安全参数为空，且不会被外层 try/except 捕获（因为异常发生在 `_persist_safety_parameters` 内部，而安全参数提取的 try/except 只包裹了 `extract_safety_parameters` 调用，没有包裹 `_persist_safety_parameters`）。

**修复建议:**
```python
raw_parameters = self.llm_client.extract_safety_parameters(text, doc.original_filename)
if raw_parameters is not None:
    self._persist_safety_parameters(tenant_id, document_id, raw_parameters)
```

或在 `_persist_safety_parameters` 入口处防御：
```python
if raw_parameters is None:
    return
```

---

## Medium 级别问题（建议修复）

### [M-1] M-3 修复不完全：空文档仍然返回 1 个参数

**位置:** `backend/app/integrations/llm_client.py:154`

**问题描述:** 第一轮评审要求移除 `max(1, ...)` 以允许返回空列表。当前代码为 `count = min(len(parameters), (text_length % 4) + 1)`。当 `text_length = 0`（空文档）时：
- `0 % 4 = 0`
- `0 + 1 = 1`
- `count = min(4, 1) = 1`

空文档仍然返回 1 个参数，与真实场景不符。

**修复建议:**
```python
count = min(len(parameters), text_length % 4)
```

这样空文档返回 0 个参数，长度为 1 的文档返回 1 个，长度为 3 的文档返回 3 个，长度为 4 的文档返回 0 个（循环）。

> 注：如果期望所有非空文档都返回至少 1 个参数，可改为 `min(len(parameters), max(0, text_length % 4))`。

---

### [M-2] 重新解析时安全参数提取失败导致数据丢失

**位置:** `backend/app/services/document_parse_service.py:76-88`

**问题描述:** `execute_parse` 的执行顺序为：
1. 删除旧安全参数（`delete_by_document`）
2. 提取并持久化新安全参数（`extract_safety_parameters` + `_persist_safety_parameters`）

如果步骤 2 失败（LLM 异常、网络超时等），旧数据已被删除且不会恢复。用户在重新解析后会发现之前存在的安全参数全部消失。

**修复建议:** 将 `delete_by_document` 移到成功提取之后，或使用事务回滚。MVP 简化的修复方案：

```python
try:
    raw_parameters = self.llm_client.extract_safety_parameters(text, doc.original_filename)
    if raw_parameters is not None:
        self.safety_repo.delete_by_document(document_id, tenant_id)
        self._persist_safety_parameters(tenant_id, document_id, raw_parameters)
except Exception:
    logger.exception("Safety parameter extraction failed for document %s", document_id)
```

这样只有在成功提取后才删除旧数据，失败时保留旧数据。

---

### [M-3] `get_safety_parameters` / `get_requirements_tree` 未检查解析状态

**位置:** `backend/app/services/document_parse_service.py:201-218`

**问题描述:** 当文档的 `parse_status` 为 `running`（解析进行中）或 `failed`（解析失败）时，`get_safety_parameters` 仍返回数据（可能是旧数据或空列表）。这可能导致用户看到不完整或误导性的结果。

**修复建议:** 在返回数据前检查 `parse_status`，如果既不是 `completed` 也不是 `running`（进行中可能已部分写入），可以考虑返回明确的提示或空结果。考虑到 `running` 状态下可能部分数据已写入，更保守的做法是：

```python
def get_safety_parameters(self, tenant_id: int, document_id: str) -> list[dict]:
    doc = self.doc_repo.get_by_id(document_id, tenant_id)
    if doc is None:
        raise DocumentNotFoundError(document_id)
    if doc.parse_status not in ("completed", "running"):
        return []
    params = self.safety_repo.get_by_document(document_id, tenant_id)
    return [...]
```

但此改动会影响 `get_requirements_tree` 的一致性，建议统一处理或作为后续优化。

---

## Low 级别问题（可选优化）

### [L-1] `SafetyParameterTable` Column render 参数命名偏离 AntD 惯例

**位置:** `frontend/src/features/documents/components/SafetyParameterTable.tsx:30`

**问题描述:** Ant Design Table 文档中 `render` 函数的标准签名为 `(text, record, index)`。当前代码使用 `(value, record)`，虽然功能正确，但偏离团队惯例，对新开发者造成认知负担。

**修复建议:**
```tsx
render: (text: string, record: SafetyParameter) => (
  <span>
    {text}
    {record.unit && <Tag style={{ marginLeft: 4 }}>{record.unit}</Tag>}
  </span>
)
```

---

## 第一轮修复验证

| 原问题 | 修复状态 | 验证结果 |
|--------|----------|----------|
| H-1 source_page 类型转换 | 已修复 | 正确，增加 int() 转换 + 异常回退 |
| H-2 value 零值误判 | 已修复 | 正确，改为 `value is None` + 空字符串校验 |
| M-1 get_safety_parameters 未校验文档 | 已修复 | 正确，增加 DocumentNotFoundError |
| M-2 安全参数失败导致解析失败 | 已修复 | 正确，独立 try/except |
| M-3 MockLLMClient 总是返回 ≥1 参数 | **修复不完全** | 空文档仍返回 1 个参数 |
| M-4 缺少反向 relationship | 已修复 | 正确，添加 `document = relationship(...)` |

---

## Acceptance Auditor — Spec 对照结果（第二轮）

| AC | 状态 | 说明 |
|----|------|------|
| AC1 | PASS | 独立编号、独立存储 |
| AC2 | PASS | 字段完整 |
| AC3 | PASS | Tabs 分区 |
| AC4 | PARTIAL | 有 relationship 和章节/页码，但前端未提供文档导航链接 |
| AC5 | PASS | 空状态提示 |

---

## 修复状态（2026-05-21）

| 问题 | 状态 | 修复位置 |
|------|------|----------|
| H-1 | 已修复 | `document_parse_service.py:execute_parse` — 增加 `if raw_parameters is not None` 检查 |
| M-1 | 已修复 | `llm_client.py` — 修正为 `text_length % 4`，空文档返回 0 个参数 |
| M-2 | 已修复 | `document_parse_service.py:execute_parse` — `delete_by_document` 移至成功提取之后 |
| M-3 | 已修复 | `document_parse_service.py:get_safety_parameters` — 增加 `parse_status` 过滤 |
| L-1 | 延后 | 记录为技术债务 |

**回归测试结果：** 后端 52 项测试全部通过，前端 6 项测试全部通过，生产构建成功。
