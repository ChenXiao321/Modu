# 默认质量检查表

本文档定义了需求分析 Agent 各步骤的默认质量检查项。

## 通用检查项（所有步骤）

- [ ] 输出格式为纯 JSON，无多余解释文字
- [ ] 输出中没有 Markdown 代码块标记（```json）

## 步骤 2 检查项（需求提取）

- [ ] 所有需求都有唯一的 requirement_id
- [ ] requirement_id 长度不超过 50 字符
- [ ] 所有需求都有非空的 description
- [ ] ASIL 等级（如有）必须是 A、B、C、D 或 QM 之一
- [ ] 需求 ID 格式符合 SW-REQ-{三位数字} 或 SW-REQ-{三位数字}-{两位数字}

## 步骤 3 检查项（ASIL 验证）

- [ ] 每条需求的 asil_level 与文档原文声明一致
- [ ] inconsistencies 数组中的每一项都有 requirement_id、issue 和 suggested_asil

## 步骤 4 检查项（层次关系）

- [ ] 需求树深度不超过 10 层
- [ ] 无循环引用（子需求不能直接或间接引用自身为祖先）
- [ ] 每个子节点的 parent_requirement_id 必须指向树中存在的节点
- [ ] 树中不存在重复的 requirement_id
