# 待办事项 — 2026-06-01

## 今日完成
- 选项 A：P1 Defer 项清理全部完成（3 项）
- Story 3.1 PRD 生成 + adversarial review（P0/P1 修复）
- Epic 2 快速回顾（状态机扩展检查清单沉淀到 story-dev-checklist.md 第 6 节）
- **Story 3.1「MISRA 合规代码自动生成」全部实现完成**
  - Task 1: GeneratedCodeFile 数据模型 + Repository ✅
  - Task 2: 2-step Agent 工作流 + Prompt 模板 + CodeGenerationService ✅
  - Task 3: POST /code-generation + GET /code-files + GET /code-files/{file_id} ✅
  - Task 4: 流水线状态扩展（code_generation_running → code_generated）✅
  - Task 5: 7 例集成测试，全量 174 passed ✅
- 提交 3 个 commit（P1 Defer 清理、PRD review 修复、Story 3.1 实现）

## 当前项目状态快照

| Epic | 状态 |
|------|------|
| Epic 1 文档上传与智能解析 | done |
| Epic 2 方案设计与审查协作 | done |
| Epic 3 合规代码自动生成 | in-progress（3.1 done，3.2/3.3 backlog） |
| Epic 4-9 | backlog |

**测试基线：** 174 passed, 0 failed
**未提交更改：** sprint-status.yaml, pending-work.md

## 下一步选项

1. **提交状态更新** → git add + git commit sprint-status.yaml + pending-work.md
2. **启动 Story 3.2**「Polarion 追溯 ID 嵌入与模板一致性」
3. **启动 Story 3.3**「ASIL 等级自适应代码生成」
4. **代码评审** — 对 Story 3.1 实现进行 adversarial review
