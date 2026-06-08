# 待办事项 — 2026-06-01

## 今日完成
- 选项 A：P1 Defer 项清理全部完成（3 项）
- Story 3.1 PRD 生成 + adversarial review（P0/P1 修复）
- Epic 2 快速回顾（状态机扩展检查清单沉淀到 story-dev-checklist.md 第 6 节）
- **Story 3.1「MISRA 合规代码自动生成」全部实现 + review + 修复完成**
  - Task 1-5 全部完成，7 例集成测试
  - adversarial code review 发现 1 P0 + 3 P1，已全部修复
- **FC 模板集成完成**
  - 复制 11 个 G-Pulse FC 模板到 app/templates/code/
  - CodeGenerationService 新增 FC 框架生成步骤
  - LLM Prompt 嵌入 FC 框架，生成 10 个文件
  - MockLLMClient 返回 10 个文件
  - author 字段使用 _DEFAULT_AUTHOR = "AI_Generated"
- 提交 8 个 commit

## 当前项目状态快照

| Epic | 状态 |
|------|------|
| Epic 1 文档上传与智能解析 | done |
| Epic 2 方案设计与审查协作 | done |
| Epic 3 合规代码自动生成 | in-progress（3.1 done，3.2/3.3 backlog） |
| Epic 4-9 | backlog |

**测试基线：** 174 passed, 0 failed
**未提交更改：** 无

## 下一步选项

1. **启动 Story 3.2**「Polarion 追溯 ID 嵌入与模板一致性」
2. **启动 Story 3.3**「ASIL 等级自适应代码生成」
3. **明天继续**
