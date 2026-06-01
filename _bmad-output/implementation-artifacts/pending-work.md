# 待办事项 — 2026-06-01

## 今日完成
- 选项 A：P1 Defer 项清理全部完成（3 项，30 分钟内）
  - 输入长度上限加固：`schemas/design_review.py` 添加 `max_length`
  - 超大事务风险修复：`_persist_ocr_results` 改批量 commit（`_OCR_BATCH_SIZE=100`）
  - 并发竞争集成测试：新增 3 个竞态场景测试
- Story 3.1 PRD 生成 + adversarial review（P0/P1 修复）
  - P0-1: `_update_pipeline_block_status` 终态保护扩展为集合
  - P0-2: PRD 增加服务隔离说明
  - P1-1: MockLLMClient 新增代码生成分支
  - P1-2: PRD 明确 Agent 输入源组织
  - P1-3: PRD 增加重新生成策略
  - P2: PRD 补充文件命名规则、JSON content 约束
- Epic 2 快速回顾（10 分钟）
  - 发现状态机管理的隐式/分散问题
  - 沉淀"新增 pipeline_status 状态强制检查清单"到 `story-dev-checklist.md`（第 6 节）
  - 生成回顾报告 `epic2-retrospective-2026-06-01.md`
- 提交今日改动（2 个 commit）

## 当前项目状态快照

| Epic | 状态 |
|------|------|
| Epic 1 文档上传与智能解析 | done |
| Epic 2 方案设计与审查协作 | done |
| Epic 3 合规代码自动生成 | in-progress（Story 3.1 ready-for-dev） |
| Epic 4-9 | backlog |

**测试基线：** 167 passed, 0 failed
**未提交更改：** 无

## 下一步

进入 **Story 3.1 实现**，按 Task 1→5 顺序开发：
- Task 1: 数据模型 + Repository（~15 分钟）
- Task 2: Agent 工作流 + Prompt 模板 + Mock + Service（~40 分钟）
- Task 3: API 端点（~15 分钟）
- Task 4: 流水线状态扩展（~10 分钟）
- Task 5: 测试（~20 分钟）
