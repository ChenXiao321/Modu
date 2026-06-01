# 待办事项 — 2026-06-01

## 今日完成
- 选项 A：P1 Defer 项清理全部完成（3 项，30 分钟内）
  - 输入长度上限加固：`schemas/design_review.py` 添加 `max_length`
  - 超大事务风险修复：`_persist_ocr_results` 改批量 commit（`_OCR_BATCH_SIZE=100`）
  - 并发竞争集成测试：新增 3 个竞态场景测试
- 测试基线更新：167 passed（+3），0 failed

## 当前项目状态快照

| Epic | 状态 |
|------|------|
| Epic 1 文档上传与智能解析 | done |
| Epic 2 方案设计与审查协作 | done |
| Epic 3 合规代码自动生成 | backlog |
| Epic 4-9 | backlog |

**测试基线：** 167 passed, 0 failed
**未提交更改：** `schemas/design_review.py`、`document_parse_service.py`、`test_design_review_router.py`、`deferred-work.md`、`pending-work.md`

## 下一步选项

1. **提交今日改动** → git commit
2. **启动 Epic 3「合规代码自动生成」** → 生成 Story 3.1 PRD / 任务拆分
3. **Epic 2 Sprint 回顾** → 基于 2.1/2.2/2.3 开发数据提炼经验教训
