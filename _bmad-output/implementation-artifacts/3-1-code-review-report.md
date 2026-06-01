# Story 3.1 代码评审报告

**Reviewer**: Claude (adversarial mode)
**Date**: 2026-06-01
**Scope**: `code_generation_service.py`, `generated_code_file_repository.py`, `documents.py` 代码生成端点, `steps.py` Agent 步骤

---

## P0 — 阻塞性问题（必须修复）

### P0-1: `trigger_generate` 缺少 `with_for_update()` 并发保护

**位置**: `code_generation_service.py:46-65`

**问题**: `trigger_generate` 检查 `pipeline_status` 和更新状态之间没有行级锁，存在 TOCTOU 竞态：

```python
def trigger_generate(self, tenant_id, document_id):
    doc = self.doc_repo.get_by_id(document_id, tenant_id)  # T1: 读状态 = design_reviewed
    if doc.pipeline_status == "code_generation_running":      # T1: 通过检查
        raise ...
    self.code_repo.delete_by_document(...)                   # T1: 删除旧文件
    # T2 同时到达，也读到 design_reviewed，也删除旧文件
    doc.pipeline_status = "code_generation_running"           # T1: 更新状态
    self.db.commit()                                          # T1: commit
    # T2 也 commit，两个后台任务同时执行 execute_generate
```

**后果**: 两个并发请求可能同时触发代码生成，产生两组冲突的代码文件。

**修复**:
```python
doc = (
    self.db.query(Document)
    .filter(Document.id == document_id, Document.tenant_id == tenant_id)
    .with_for_update()
    .first()
)
```

---

## P1 — 高风险问题（建议修复）

### P1-1: `execute_generate` 中 `code_repo.create` 逐条 commit

**位置**: `code_generation_service.py:119-128`

**问题**:
```python
for f in files:
    self.code_repo.create(...)  # 每次 create 内部调用 db.commit()
```

如果模块生成 10 个文件，会执行 10 次 commit。如果在第 6 个文件时失败，前 5 个已持久化且无法回滚。

**修复**: 在 Service 层统一事务：
```python
for f in files:
    record = GeneratedCodeFile(...)
    self.db.add(record)
self.db.commit()  # 统一 commit
```

---

### P1-2: `trigger_generate` 中 delete 与状态更新不在同一事务

**位置**: `code_generation_service.py:58-64`

**问题**:
```python
self.code_repo.delete_by_document(document_id, tenant_id)  # 独立 commit
# 如果这里抛异常（如数据库断开），旧文件已删但状态未变
doc.pipeline_status = "code_generation_running"
self.db.commit()
```

**修复**: 将 delete 逻辑内联到 Service 层，与状态更新共享同一会话：
```python
self.code_repo.delete_by_document(document_id, tenant_id)  # 改为不自行 commit
# 或者直接在 Service 层执行 query().delete()
doc.pipeline_status = "code_generation_running"
self.db.commit()
```

> **注意**: 这需要修改 `GeneratedCodeFileRepository.delete_by_document` 去掉内部 commit，或新增一个 `delete_by_document_no_commit` 方法。参考 `story-dev-checklist.md` 第 2.1 条：Repository 不应自行 commit。

---

### P1-3: `_mark_failed` 未清理已部分创建的代码文件

**位置**: `code_generation_service.py:214-223`

**问题**: `execute_generate` 在 `for f in files: self.code_repo.create(...)` 过程中可能失败（如第 5 个文件创建后 Agent 报错）。`_mark_failed` 只回滚 `pipeline_status`，没有删除已部分创建的文件。

**后果**: 数据库中残留部分代码文件，用户查询时会看到不完整的产物。

**修复**:
```python
def _mark_failed(self, document_id, tenant_id, error_message):
    self.code_repo.delete_by_document(document_id, tenant_id)
    doc = self.doc_repo.get_by_id(document_id, tenant_id)
    if doc is not None and doc.pipeline_status == "code_generation_running":
        doc.pipeline_status = "design_reviewed"
        doc.block_reason = None
        self.db.commit()
```

---

## P2 — 改进建议（可选）

### P2-1: `get_code_file_by_id` 异常语义不当

**位置**: `code_generation_service.py:166-168`

```python
if f is None or f.document_id != document_id:
    raise DesignDocumentNotFoundError(file_id)
```

`DesignDocumentNotFoundError` 的错误消息是"设计文档未找到"，但实际是代码文件未找到。虽然 HTTP 状态码都是 404，但错误消息会误导客户端调试。

**建议**: 新增 `CodeFileNotFoundError` 异常类，或复用更通用的 `DocumentNotFoundError`。

---

### P2-2: `parse_output` 对 LLM 非法 JSON 换行符无兜底清洗

**位置**: `steps.py:506-509`

```python
cleaned = _clean_json_response(raw)
try:
    data = json.loads(cleaned)
except json.JSONDecodeError as exc:
    raise LLMOutputFormatError(...)
```

如果 LLM 在 JSON 字符串值内直接插入未转义的换行符（常见错误），`json.loads` 会失败。虽然 Prompt 中明确要求了 `\n` 转义，但 LLM 不总是遵守。

**建议**: 在 `json.loads` 前增加一层兜底清洗：将 JSON 字符串值内的裸换行符替换为 `\n`。这是一个已知 LLM 输出问题，可以作为 P2 Defer 留给后续迭代。

---

## 统计

| 级别 | 数量 |
|------|------|
| P0 | 1 |
| P1 | 3 |
| P2 | 2 |

---

## 修复优先级

1. **P0-1** `with_for_update()` — 直接影响并发安全
2. **P1-3** `_mark_failed` 清理残留文件 — 直接影响数据一致性
3. **P1-1** 批量 commit — 影响事务原子性
4. **P1-2** delete 与状态更新同一事务 — 影响事务原子性
5. **P2** 可选改进
