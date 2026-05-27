# Deferred Work

## Deferred from: code review of 2-1-design-document-auto-generation (2026-05-25)

- `DesignDocumentRepository.create` 无显式 rollback 处理 [backend/app/repositories/design_document_repository.py:231-235] — pre-existing SQLAlchemy session 管理模式
- 前端 `DesignDocument.status` 类型为 `string` 而非字面量联合 [frontend/src/features/documents/types.ts:1458-1469] — TypeScript 增强
- `document_id` URL 参数无 UUID 格式校验 [backend/app/routers/v1/documents.py:290-311] — 项目范围路由校验模式
- `MockLLMClient` trace ID 基于 `len(filename) % 1000` 易碰撞 [backend/app/integrations/llm_client.py:74] — Mock 已知限制
- `_build_requirements_list` 递归遍历 `r.children` 存在跨租户泄漏假设 [backend/app/services/design_document_service.py:428,541] — 无实证
- `TimestampMixin` 的 `onupdate` 行为未在 diff 中验证 [backend/app/models/design_document.py] — pre-existing

## Deferred from: code review of 2-2-design-document-split-screen-review-and-online-correction (2026-05-27)

- `DesignRevision` 缺少 `reason`/`change_description` 字段 — 功能增强，deferred
- Pydantic schema 缺少 `max_length` 限制 — 待后续统一加固
- `author` 字段为自由文本无格式校验 — Auth 模块实现后统一处理
- `_compute_diff` 对超大输入无保护 — MVP 边界情况
- 缺少 `(document_id, section_key)` 复合索引 — 性能优化 deferred
- `_VALID_SECTION_KEYS` 与 `_REQUIRED_SECTIONS` 硬编码重复 — 架构层面后续统一
- 前端缺少重试/离线处理 — 功能增强 deferred
- 缺少 Error Boundary / 按章节错误隔离 — 架构层面 deferred
