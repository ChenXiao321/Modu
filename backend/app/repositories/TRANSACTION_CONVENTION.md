# Repository 事务边界约定

## 核心原则

**Service 层拥有事务控制权。** Repository 层提供两种模式，调用方必须根据场景选择正确的一种。

| 模式 | Repository 方法 | 是否 commit | 适用场景 |
|------|----------------|------------|---------|
| **注册模式** | `add(obj)` | ❌ 不 commit | 跨 Repository 组合操作、需要原子性保证的业务流程 |
| **自包含模式** | `create(obj)` | ✅ 内部 commit + refresh | 简单独立 CRUD、单表操作、不需要与外部状态原子绑定的场景 |

## 规则

### 1. 跨 Repository 组合操作 → 必须使用注册模式

当一次业务操作涉及**多个实体变更**（如保存修订记录 + 更新设计文档），Service 层必须：
- 调用各 Repository 的 `add()` / `update()`（不 commit）
- 在 Service 层末尾统一 `self.db.commit()`

**反例**（已修复）：
```python
# ❌ 错误：revision 已 commit，design update 又在独立 commit
self.revision_repo.create(revision)  # 内部 commit
self.design_repo.update_status(...)   # 又 commit
```

**正例**（Story 2.2 模式）：
```python
# ✅ 正确：统一事务边界
self.revision_repo.add(revision)
design.sections = ...
self.db.commit()
self.db.refresh(revision)
self.db.refresh(design)
```

### 2. 简单独立 CRUD → 可使用自包含模式

单表查询、单条插入且无需与外部状态绑定的操作，可使用 `create()` 以简化代码。

```python
# ✅ 可接受：独立操作，无需原子性
self.doc_repo.create(document)
```

### 3. 禁止混合模式

同一次业务逻辑的不同分支**不得混用**两种模式。

**反例**（已修复于 `design_document_service.py`）：
```python
# ❌ 错误：existing 分支 Service commit，new 分支 Repository commit
if existing is not None:
    existing.status = "running"
    self.db.commit()          # Service 层 commit
else:
    self.design_repo.create(doc)  # Repository 内部 commit
```

### 4. Repository 层不得隐藏副作用

所有在内部 commit 的方法必须命名为 `create_xxx` 或 `update_xxx`，不得使用 `add_xxx` 命名来包装 commit。

## 当前各 Repository 支持情况

| Repository | `add()` | `create()`（内部 commit） | 状态 |
|-----------|---------|--------------------------|------|
| DocumentRepository | ❌ | ✅ `create()` | 早期实现，以自包含为主 |
| RequirementRepository | ✅ | ✅ `create()` | 已补充 `add()` |
| SafetyParameterRepository | ✅ | ✅ `create()` | 已补充 `add()` |
| DesignDocumentRepository | ✅ | ✅ `create()` / `update_status()` | 已补充 `add()` |
| OcrResultRepository | ✅ | ✅ `create()` | Story 1.4，已有 `add()` |
| DesignRevisionRepository | ✅ | ✅ `create()` | Story 2.2，双模式 |
| ReviewCommentRepository | ✅ | ✅ `create()` | Story 2.2，双模式 |

## 已知技术债务

### `_persist_requirements` 逐条 commit

`DocumentParseService._persist_requirements()` 使用递归逐条 `req_repo.create()`，每个节点独立 commit。原因是早期 `ParsedRequirement` 使用 `uuid.uuid4()` 客户端生成 ID，理论上可改为统一 `add()` + 末尾 `commit()`，但涉及递归深度和现有测试稳定性，暂未改动。

**触发条件**：需求树重构或性能优化迭代。

### `_persist_safety_parameters` 逐条 commit

同上，`SafetyParameterRepository.create()` 在循环内逐条 commit。

### `delete_by_document` 内部 commit

`RequirementRepository.delete_by_document()` 和 `SafetyParameterRepository.delete_by_document()` 在删除后内部 commit。当前 `execute_parse` 流程中，delete 与后续 persist 之间已有 commit，故不构成原子性问题，但无法保证 "delete + re-insert" 的原子性。

## 新 Story 开发检查项

- [ ] 涉及多实体变更时，确认所有 Repository 调用的是 `add()` / `update()` 而非 `create()`
- [ ] Service 方法末尾有显式的 `self.db.commit()`
- [ ] 异常路径有 `self.db.rollback()`（或依赖 SQLAlchemy 会话自动回滚）
- [ ] 同一 Service 方法的不同分支使用一致的事务模式
