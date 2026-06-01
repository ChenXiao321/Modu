# Story 开发检查清单

> 基于 Story 1.4 / 2.1 / 2.2 代码评审数据提炼。三个 Story 累计 7 轮评审、~160 项发现、92 项 Patch。以下 5 类问题跨 Story 反复出现，占 Patch 总数的 60% 以上。
> **规则**：新 Story 开发开始前，dev-agent 须通读本清单；自测阶段须逐项勾选。

---

## 1. 并发竞态（TOCTOU）

**典型场景**：多用户同时操作同一资源，或后台任务与前台查询交叉执行。

| # | 检查点 | 常见反例 | 正确做法 |
|---|--------|---------|---------|
| 1.1 | 任何"先读后写"的状态变更是否使用了行级锁？ | `if doc.status != "running": doc.status = "running"; db.commit()` | `db.query(Model).filter(...).with_for_update()` 后读取并更新 |
| 1.2 | 后台任务调度前是否已对运行中状态做原子拒绝？ | 查询状态与启动任务之间有时间窗口 | 查询 + 状态更新在同一会话内完成，再投递 BackgroundTasks |
| 1.3 | 聚合校验（如"所有评论已解决"）与状态推进是否原子？ | 先 `count(pending) == 0`，再 `update status` | 使用 `with_for_update()` 锁定父记录后重查并更新 |
| 1.4 | Repository `delete` + `insert` 组合是否在同一事务？ | 先 `delete_by_document` commit，再 `persist_ocr_results` 又 commit | 将删除逻辑移入 persist 方法内部，统一事务边界 |

**Story 历史**：1.4 `confirm_low_confidence_field`、2.1 `trigger_generate`、2.2 `save_revision` / `submit_design_review` 均在此踩坑。

---

## 2. 事务边界

**核心原则**：Repository 层不自行 `commit`，`commit` 权限归 Service 层；除非方法命名明确包含 `_and_commit`。

| # | 检查点 | 常见反例 | 正确做法 |
|---|--------|---------|---------|
| 2.1 | Repository 方法内部是否调用了 `db.commit()`？ | `repo.create()` 内部自行 commit | Repository 只做 `db.add()` + `db.flush()`，由 Service 统一 commit |
| 2.2 | 跨 Repository 的组合操作是否在同一事务？ | `revision_repo.create()` 已 commit，再 `design_repo.update()` 又 commit | Service 层内统一会话，所有 repo 操作共享同一会话后统一 commit |
| 2.3 | 循环内是否逐条 commit？ | `for item in items: repo.create(item); db.commit()` | 循环内只 add/flush，循环外统一 commit；或批量插入 |
| 2.4 | 异常时是否有显式 rollback？ | 只有 `db.commit()`，没有 `try/except/rollback` | Service 层用 `try: ... db.commit() except: db.rollback(); raise` |

**Story 历史**：1.4 `_persist_ocr_results` 逐条 commit、2.2 `save_revision` / `rollback_to_revision` 跨 repo 双 commit、2.2 `comment_repo.resolve` 自行 commit。

---

## 3. 前端 API 响应校验

**核心原则**：HTTP 200 ≠ 业务成功。后端返回统一包装 `{success, data, error, trace_id}`，前端必须校验 `success` 字段。

| # | 检查点 | 常见反例 | 正确做法 |
|---|--------|---------|---------|
| 3.1 | 每个 API 调用是否校验了 `res.data?.success`？ | `return res.data.data` 直接返回 | `if (!res.data?.success) throw new ApiError(res.data?.error)` |
| 3.2 | 校验逻辑是否防御了 `res.data` 为 undefined 的情况？ | `if (res.data.success === false)` | `if (res.data?.success === false)` 或统一包装函数 |
| 3.3 | 是否所有 API 函数共用同一套响应包装器？ | 每个 API 文件各自手写 `success` 判断 | 在 `api.ts` 中引入 `checkSuccess(response)` 高阶函数，所有 API 统一调用 |
| 3.4 | 错误时是否将 `trace_id` 带上便于后端定位？ | 只抛 `请求失败` | 错误信息包含 `trace_id: ${res.data?.trace_id}` |

**Story 历史**：1.4 `getOcrResults`/`confirmOcrField`、2.2 全量 API 函数均缺失 `success` 校验。

---

## 4. 异常处理

**核心原则**：异常处理追求"可追溯"，而非仅仅"不崩"。原始错误信息和 traceback 必须保留。

| # | 检查点 | 常见反例 | 正确做法 |
|---|--------|---------|---------|
| 4.1 | `except Exception` 是否过于宽泛？ | `except Exception: pass` 或只返回 `failed` | 捕获具体异常类型；必须用 `except Exception as exc:` 并保存 `str(exc)` |
| 4.2 | 异常时是否静默吞掉错误，导致状态不一致？ | OCR 提取失败仍标记文档 `completed` | 异常时标记文档状态为 `failed`，并将错误信息持久化到 `error_message` 字段 |
| 4.3 | 嵌套 try 块中是否重新定义了可能失败的依赖？ | 内层 try 中 `design_repo = DesignDocumentRepository(db)` 可能再次抛异常 | 将 repo 实例提至 try 块外初始化 |
| 4.4 | 异常信息是否被正确传递到外层的 error response？ | `execute_generate` 吞掉 LLM 原始错误，只返回 `"生成失败"` | `except Exception as exc: error_message = str(exc)` 并回传 |

**Story 历史**：1.4 `execute_parse` 静默吞 OCR 异常、2.1 `execute_generate` 吞原始错误、2.1 `_run_generate` 嵌套 try 二次失败。

---

## 5. 输入校验与边界情况

**核心原则**：不要相信任何外部输入（用户请求、LLM 返回、Mock 数据）。校验必须在 Service 层或 Pydantic schema 层完成，不能仅靠前端。

| # | 检查点 | 常见反例 | 正确做法 |
|---|--------|---------|---------|
| 5.1 | 字符串字段是否校验了空字符串和纯空格？ | Pydantic `min_length=1` 允许 `" "` | Service 层增加 `.strip()` 校验：`if not revised_content.strip(): raise` |
| 5.2 | 数值字段是否校验了 NaN / inf / 负值？ | `confidence: float` 未校验 `math.isnan(v)` | `if not (0.0 <= v <= 1.0) or math.isnan(v): raise ValidationError` |
| 5.3 | 枚举/标签字段是否在校验白名单后使用？ | 直接取 LLM 返回的字符串作为 `asil_level` | 增加 `valid_levels = {"A", "B", "C", "D"}` 过滤，非法值降级或抛错 |
| 5.4 | 输入长度是否设置了上限？ | `extracted_text: TEXT` 无长度限制 | 增加 `_MAX_EXTRACTED_TEXT_LEN = 10000` 并校验 |
| 5.5 | 递归/树形结构是否设置了深度上限？ | 需求树循环引用导致栈溢出 | 增加 `_MAX_TREE_DEPTH = 10`，超限时抛 `ValueError` |
| 5.6 | 排序/列表查询是否对时间戳相同的情况做了确定性处理？ | 按 `created_at.desc()` 排序，时间戳相同时顺序随机 | 增加二级排序：`created_at.desc(), id.desc()` |

**Story 历史**：1.4 `ConfirmFieldRequest` 空值、2.1 ASIL 非法值、2.2 `SaveRevisionRequest` 空字符串、2.2 时间戳排序非确定性。

---

## 6. 状态机扩展（Epic 2 回顾沉淀）

**核心原则**：新增 `pipeline_status`（或任何状态字段）时，必须做"全量 grep 影响分析"，不能只做"点修复"。终态保护必须是集合，不能是单个状态值。

| # | 检查点 | 常见反例 | 正确做法 |
|---|--------|---------|---------|
| 6.1 | 新增状态前是否运行了 `grep -rn "pipeline_status" backend/app/` 并逐条审查？ | 只改了 `_update_pipeline_block_status`，漏了 `_assert_not_locked` 和 `confirm_ocr_field` | 新增 checklist，强制审查所有引用点 |
| 6.2 | 终态保护是否使用集合而非单点硬编码？ | `if status == "in_design": return` | `_PROTECTED_STATUSES = {"in_design", "design_reviewed", "code_generated"}` |
| 6.3 | 新增终态后，`_assert_not_locked` / `DesignReviewLockedError` 是否需要扩展？ | `code_generated` 下仍可保存修订 | 评审并决定新终态是否也应锁定修改 |
| 6.4 | Schema 中状态字段是否从 `str` 升级为 `Literal` 枚举？ | `pipeline_status: str` | `pipeline_status: Literal["ready", "blocked", "in_design", "design_reviewed", "code_generated"]` |
| 6.5 | 状态转换图是否在 PRD 中定义？ | PRD 只写"完成后状态变为 X" | PRD 中画状态图：哪些状态可以转到 X，X 可以转到哪些状态 |

**Story 历史**：Epic 2 `_update_pipeline_block_status` 只保护 `in_design`，漏了 `design_reviewed`；Epic 3 评审发现后修复为集合保护。

---

## 快速自检表（开发完成时勾选）

```
□ 所有"先读后写"状态变更已加 with_for_update()
□ Repository 内无自行 commit，统一由 Service 层控制
□ 前端所有 API 调用已接入 checkSuccess() 包装器
□ 无裸 except Exception: pass；所有异常保留 str(exc)
□ Service 层对所有外部输入做了 .strip() / 范围 / 长度校验
□ 新增/修改的 router 端点已写集成测试
□ 全量单元测试通过，零回归
```

---

## 附录：评审流程提示

- **第一轮评审前**：先运行 `pytest` 全量测试，确保基线全绿；再自检本清单。
- **第二轮评审触发条件**：第一轮 Patch 修复后，换用不同上下文或评审策略（如侧重并发/边界），专门复查第一轮中 Defer 和 Dismiss 的项。
- **Defer 项管理**：任何 Defer 必须写入 `deferred-work.md`，标注触发条件、关联 Story、预期解决迭代。
