# Deferred Work 追踪清单

> 汇总 Story 1.4 / 2.1 / 2.2 全部代码评审 Defer 项，按类别和优先级组织。> **规则**：每个迭代开始前回顾本清单，评估是否有 Defer 项的触发条件已满足。

---

## 统计概览

| 来源 | Defer 数量 |
|------|-----------|
| Story 1.4 OCR 置信度 | 9 |
| Story 2.1 设计文档生成 | 6 |
| Story 2.2 分屏审查 R1 | 8 |
| Story 2.2 分屏审查 R2 | 5 |
| **合计** | **28** |

---

## 1. 架构与代码质量（8 项）

| 优先级 | 触发条件 | 关联 Story | 描述 | 位置 |
|--------|---------|-----------|------|------|
| P1 | 新增流水线终态（如 `in_test`） | 1.4 | `_update_pipeline_block_status` 终态硬编码为 `in_design`，新增终态时需扩展 | `document_parse_service.py:336` |
| P1 | 引入真实 LLM/OCR 引擎 | 1.4 | `MockLLMClient` 测试覆盖盲区：固定返回 3 个高置信度字段时，核心解阻塞路径未被覆盖 | `llm_client.py:571` |
| P2 | 架构统一重构 | 2.2 | `_VALID_SECTION_KEYS` 与 `_REQUIRED_SECTIONS` 硬编码重复，需统一为单一数据源 | `design_review_service.py` |
| P2 | 前端架构升级 | 2.2 | 缺少 Error Boundary / 按章节错误隔离 | 前端全局 |
| P2 | Auth 模块实现 | 2.1, 2.2 | `author` 字段为自由文本无格式校验，Auth 实现后统一替换为 `CurrentUser` | 多文件 |
| P2 | 前端 TypeScript 严格化 | 2.1 | 前端 `DesignDocument.status` 类型为 `string` 而非字面量联合 | `types.ts:1458-1469` |
| P2 | 数据模型增强 | 2.2 | `DesignRevision` 缺少 `reason`/`change_description` 字段 | `models/design_revision.py` |
| P2 | 验证需求 | 2.1 | `TimestampMixin` 的 `onupdate` 行为未在 diff 中验证 | `models/design_document.py` |

---

## 2. 性能优化（6 项）

| 优先级 | 触发条件 | 关联 Story | 描述 | 位置 |
|--------|---------|-----------|------|------|
| ~~P1~~ ✅ | ~~单文档 > 50 页或字段 > 1000 条~~ | 1.4 | ~~`_persist_ocr_results` 超大事务风险：全量字段一次 commit~~ → 改批量 commit（`_OCR_BATCH_SIZE=100`） | `document_parse_service.py:291` |
| P1 | 大文档分屏审查卡顿 | 2.2 | 前端大数组未做懒加载/分页（requirements、safetyParameters） | `DesignReviewPage.tsx` |
| P2 | 数据库性能调优迭代 | 2.2 | 缺少 `(document_id, section_key)` 复合索引 | Alembic 迁移 |
| P2 | 性能调优迭代 | 2.2 | `get_review_context` 一次性加载全量评论/需求/安全参数，大文档时负载风险 | `design_review_service.py:49` |
| P2 | 性能调优迭代 | 2.1 | `get_review_context` 使用 5 次顺序查询，可优化为 JOIN 或并行查询 | `design_review_service.py`（如有） |
| P2 | 性能调优迭代 | 2.2 | `_compute_diff` 对超大输入无保护 | `design_review_service.py` |

---

## 3. 输入校验与加固（5 项）

| 优先级 | 触发条件 | 关联 Story | 描述 | 位置 |
|--------|---------|-----------|------|------|
| ~~P1~~ ✅ | ~~安全审计 / 渗透测试~~ | 2.2 | ~~无输入长度上限~~ → 添加 `max_length`（`revised_content`=50K, `comment_text`=10K, `author`=100） | `schemas/design_review.py` |
| P2 | 安全加固迭代 | 1.4 | reviewerName 输入框无前端最大长度限制 | `RequirementViewerPage.tsx:1798` |
| P2 | Pydantic 统一加固 | 2.2 | Pydantic schema 缺少 `max_length` 限制 | 全局 schema |
| P2 | 安全加固迭代 | 2.1 | `document_id` URL 参数无 UUID 格式校验 | `routers/v1/documents.py:290-311` |
| P2 | 安全加固迭代 | 1.4 | `get_low_confidence_count` 的 `threshold` 参数 NaN/inf 校验可进一步完善 | `ocr_result_repository.py:106` |

---

## 4. 并发与事务（3 项）

| 优先级 | 触发条件 | 关联 Story | 描述 | 位置 |
|--------|---------|-----------|------|------|
| ~~P1~~ ✅ | ~~高并发场景验证~~ | 2.2 | ~~缺少并发竞争场景的集成测试~~ → 新增 3 个竞态测试（重复提交、修订链一致性、重复 resolve） | `tests/integration/test_design_review_router.py` |
| P2 | SQLAlchemy 会话重构 | 1.4 | `update_review_status_atomic` 会话同步隐患 | `ocr_result_repository.py:147` |
| P2 | 高并发场景验证 | 2.2 | `submit_design_review` 幂等性未处理（缺少幂等键） | `design_review_service.py` |

---

## 5. 前端健壮性（4 项）

| 优先级 | 触发条件 | 关联 Story | 描述 | 位置 |
|--------|---------|-----------|------|------|
| P2 | 前端优化迭代 | 1.4 | `OcrResultTable` `onRow` style 对象引用可能导致重渲染 | `OcrResultTable.tsx:166` |
| P2 | 前端优化迭代 | 2.2 | 前端缺少重试/离线处理 | 前端全局 |
| P2 | 前端优化迭代 | 2.2 | `SectionEditor` draft 未同步外部 content prop 变化（已修复但需验证模式） | `SectionEditor.tsx` |
| P2 | 前端优化迭代 | 2.2 | `localStorage` 缓存策略可扩展为草稿文本自动保存 | `DesignReviewPage.tsx` |

---

## 6. 测试质量（2 项）

| 优先级 | 触发条件 | 关联 Story | 描述 | 位置 |
|--------|---------|-----------|------|------|
| P2 | 测试重构 | 1.4 | 测试中断言过于宽泛（`pytest.raises(Exception)`），应使用具体异常类型 | `test_document_parse_service_ocr.py:568` |
| P2 | 测试重构 | 1.4 | `source_page` 类型错误静默吞掉，建议添加日志警告并补充测试 | `document_parse_service.py:315` |

---

## 迭代回顾检查项

每次启动新 Story 前，按以下顺序评估 Defer 项：

1. **Auth 模块是否已落地？** → 处理所有 `author` 字段相关 Defer（5 项）
2. **是否涉及新的流水线终态？** → 处理 `_update_pipeline_block_status` 硬编码（1 项）
3. **是否新增 Pydantic Schema？** → 统一加固 `max_length` 和类型联合（3 项）
4. **是否涉及大文档（>50 页）场景？** → 处理性能相关 Defer（4 项）
5. **是否引入真实 LLM？** → 处理 Mock 测试覆盖盲区（1 项）
