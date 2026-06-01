# Epic 2 Sprint 快速回顾 — 2026-06-01

**Trigger**: Story 3.1 adversarial review 发现 `_update_pipeline_block_status` 终态保护缺失
**Duration**: 10 分钟
**Scope**: 状态机扩展模式分析 + 检查清单沉淀

---

## 核心发现

### 1. 状态机管理是隐式的、分散的

`pipeline_status`（`String(20)`）的状态值硬编码在 **5 个文件、15+ 个位置**：

| 状态值 | 硬编码位置数 | 主要文件 |
|--------|------------|---------|
| `"ready"` | 5 | `document_parse_service.py`, `design_document_service.py` |
| `"blocked"` | 5 | `document_parse_service.py`, `design_document_service.py` |
| `"in_design"` | 6 | `document_parse_service.py`, `design_document_service.py`, `design_review_service.py` |
| `"design_reviewed"` | 4 | `design_document_service.py`, `design_review_service.py` |

**问题**：
- 没有集中的 `PipelineStatus` 枚举或常量定义
- 没有状态转换图，没有终态/中间态的显式声明
- Schema 中 `pipeline_status` 都是 `str` 类型，前端无法从类型层面知道合法值域
- 新增状态时，无法系统性地找到所有需要更新的位置

---

### 2. `_update_pipeline_block_status` 的终态保护为什么是"点修复"

**原代码**（Epic 2 批次 1）：

```python
# Protect in_design state: once entered design phase, do not revert
if doc.pipeline_status == "in_design":
    return
```

**Epic 2 当时已有 `"design_reviewed"` 终态**，但 `_update_pipeline_block_status` 没有保护它。

**为什么评审没发现？**

| 原因 | 说明 |
|------|------|
| **需求聚焦** | Epic 2 PRD 只定义了 `ready` → `blocked` → `in_design` → `design_reviewed`，没有考虑 Epic 3/4/5 的状态扩展 |
| **注释误导** | 注释明确说 "Protect in_design state"，评审者可能认为这是有意为之的设计决策 |
| **调用链假设** | `_update_pipeline_block_status` 只在 `_run_parse` 中调用，开发者假设它不会在 review 后执行 |
| **缺少检查清单** | 没有"新增状态影响分析"的标准化检查项 |

**修复**（2026-06-01）：
```python
_PROTECTED_STATUSES = {"in_design", "design_reviewed", "code_generated"}
if doc.pipeline_status in self._PROTECTED_STATUSES:
    return
```

---

### 3. 其他硬编码状态检查的风险扫描

#### 3.1 `confirm_ocr_field` — `pipeline_status != "blocked"`

```python
# document_parse_service.py:480
if doc.pipeline_status != "blocked":
    raise PipelineNotBlockedError(document_id)
```

**风险**：只有在 `blocked` 状态下才能 confirm OCR 字段。如果未来某个中间态（如 `code_generation_running`）也需要 confirm OCR，这个检查会拒绝。

**评估**：低风险。OCR confirm 只应在解析/审查前阶段发生，终态下不应触发。且 `_PROTECTED_STATUSES` 修复后，`_update_pipeline_block_status` 在终态下直接 return，不会执行到 confirm 后的状态重算。

#### 3.2 `execute_generate` 失败回滚 — `pipeline_status == "in_design"`

```python
# design_document_service.py:189
if doc is not None and doc.pipeline_status == "in_design":
    doc.pipeline_status = "ready"
```

**风险**：如果未来允许在 `design_reviewed` 状态下重新生成设计文档（例如设计审查通过后用户决定重新生成），失败时不会回滚（因为条件不满足）。

**评估**：中低风险。当前 PRD 明确禁止在 `design_reviewed` 后重新生成设计文档，但长期可能支持"重新设计"。

#### 3.3 `_assert_not_locked` — `pipeline_status == "design_reviewed"`

```python
# design_review_service.py:108
if doc is not None and doc.pipeline_status == "design_reviewed":
    raise DesignReviewLockedError(document_id)
```

**风险**：`code_generated` 也是终态，但 `_assert_not_locked` 不会阻止在 `code_generated` 状态下保存修订/添加评论。

**评估**：中风险。设计审查通过并生成代码后，理论上设计应被冻结。PRD 未明确是否允许在 `code_generated` 后修改设计，留到后续迭代评估。

---

## 经验教训

### 经验 1: 状态机扩展必须做"全量 grep 影响分析"

新增一个状态值前，必须运行：
```bash
grep -rn "pipeline_status" backend/app/
```
并逐条审查每个引用点是否需要更新。

### 经验 2: 终态保护必须是"集合"而非"单点"

任何判断"是否是终态"的逻辑，必须使用集合/枚举，不能硬编码单个状态值：

```python
# ❌ 错误 — 点保护
if doc.pipeline_status == "in_design": return

# ✅ 正确 — 面保护
_PROTECTED_STATUSES = {"in_design", "design_reviewed", "code_generated"}
if doc.pipeline_status in _PROTECTED_STATUSES: return
```

### 经验 3: 字符串硬编码 = 技术债务

`pipeline_status` 使用 `String(20)` 而非 `Enum`，导致：
- 编译期无法发现拼写错误（如 `"desgin_reviewed"`）
- IDE 无法自动补全合法状态值
- 新增状态时容易遗漏引用点

**建议长期改进**：
1. 使用 Python `StrEnum` 定义 `PipelineStatus`
2. Pydantic Schema 中使用 `Literal` 类型
3. SQLAlchemy 中使用 `Enum` 列类型（PostgreSQL 支持原生 enum）

---

## 沉淀检查清单

### 新增 `pipeline_status` 状态时的强制检查项

每次新增状态，必须完成以下检查（copy 到 Story 任务列表）：

```markdown
- [ ] `_update_pipeline_block_status._PROTECTED_STATUSES` 是否包含新终态
- [ ] `_assert_not_locked` / `DesignReviewLockedError` 是否应阻止新终态下的修改
- [ ] `trigger_generate`（设计文档生成）的前置条件是否需要更新
- [ ] `submit_design_review` 的前置条件是否需要更新
- [ ] `confirm_ocr_field` 的状态检查是否需要更新
- [ ] `execute_generate` 失败回滚逻辑是否需要更新
- [ ] Schema 中 `pipeline_status` 的 `Literal` 类型是否需要扩展
- [ ] 运行 `grep -rn "pipeline_status" backend/app/` 审查所有引用点
- [ ] 新增集成测试覆盖"旧终态下触发新流程"的拒绝场景
```

---

## 对 Epic 3 的直接影响

1. **Task 4（流水线状态扩展）** 已加入上述检查清单作为 Subtask 4.4
2. **`_assert_not_locked`** 当前不阻止 `code_generated` 下的修改 — 这在 Story 3.1 的范围内是可接受的（PRD 未要求锁定代码生成后的设计），但需要在 deferred-work.md 中标记为 P2 待评估项
3. **Schema 类型约束** 当前仍为 `str`，建议在 Epic 3 收尾阶段统一升级为 `Literal` 枚举（作为 P2 技术债务清理）

---

## Action Items

| # | 行动 | 负责人 | 优先级 | 截止 |
|---|------|--------|--------|------|
| 1 | 将上述检查清单写入 `story-dev-checklist.md` | Dev | P1 | 2026-06-01 |
| 2 | 在 `deferred-work.md` 中标记 `_assert_not_locked` 对 `code_generated` 的处理为 P2 Defer | Dev | P2 | Epic 3 收尾 |
| 3 | Epic 3 收尾时评估 `PipelineStatus` StrEnum 重构 | Dev | P2 | Epic 3 收尾 |
