# 需求分析阶段检查表

本文档定义了 FC 需求规范提取 Agent 各步骤的质量检查项。

## 通用检查项（所有步骤）

- [ ] 输出格式为纯 JSON，无多余解释文字
- [ ] 输出中没有 Markdown 代码块标记（```json）

## 步骤 1 检查项（文档结构分析）

- [ ] chapters 必须覆盖文档中所有显式编号章节
- [ ] key_terms 应包含对理解需求至关重要的缩写和专有名词
- [ ] document_type 正确识别为 chip_manual 或 requirement_spec

## 步骤 2 检查项（需求提取）

- [ ] 所有需求都有唯一的 requirement_id
- [ ] requirement_id 长度不超过 50 字符
- [ ] 所有需求都有非空的 description
- [ ] ASIL 等级（如有）必须是 A、B、C、D 或 QM 之一
- [ ] 需求 ID 格式符合 SW-REQ-{三位数字} 或 SW-REQ-{三位数字}-{两位数字}

## 步骤 3 检查项（ASIL 验证）

- [ ] 每条需求的 asil_level 与文档原文声明一致
- [ ] inconsistencies 数组中的每一项都有 requirement_id、issue 和 suggested_asil

## 步骤 4 检查项（FC 需求规范生成）

- [ ] purpose 字段非空，且基于文档原文生成
- [ ] scope 字段非空，明确覆盖范围
- [ ] definitions 包含文档中的关键缩写和专有名词
- [ ] overview 描述需求背景、软件架构、功能框图
- [ ] functional_requirements 按 BSW 和 ASW 分组
- [ ] 每个功能性需求包含 requirement_id、description、chapter、asil_level
- [ ] non_functional_requirements 包含 MISRA 2012、建模规范等非功能性约束
- [ ] 需求树深度不超过 10 层
- [ ] 无循环引用
- [ ] 不存在重复的 requirement_id
