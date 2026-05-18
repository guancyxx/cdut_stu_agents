# 学生学习状态管理解决方案（cdutstuagents / ai-agent-lite）

## 1. 背景与目标

当前系统已具备以下能力：
- 会话级状态持久化（`sessions.supervisor_state`）
- 基础状态字段（`knowledge_graph_position`、`emotion_tags`、`efficiency_trend`、`last_agent_type`）
- 单轮知识增量评估（`KnowledgeAssessor.assess`）
- 基于 state delta 的 NextStepSuggester

但仍存在核心缺口：
- 状态“只有快照，没有事件历史”，难以回溯“为什么变化”
- 学习进展仅在会话维度，缺少“用户长期状态”
- 缺少可解释的学习状态指标体系（掌握度、稳定度、风险度）
- 缺少状态驱动的干预策略（什么时候鼓励、什么时候降难、什么时候复习）

本方案目标：
1) 构建“会话态 + 用户长期态 + 事件流”三层学习状态模型
2) 形成可解释、可追踪、可干预的学习状态闭环
3) 不破坏现有 websocket/chat 主流程，采用可渐进落地方案

---

## 2. 设计原则

1. 渐进式改造
- 复用现有 `StateManager` 与 `conversation_orchestrator` 管线
- 先加事件与指标，再逐步接入推荐/路由

2. 单一职责
- `state_manager.py` 负责“状态读写”
- 新增 `learning_state_service.py` 负责“指标计算与状态聚合”
- 新增 `learning_event_repo.py` 负责“事件落库”

3. 可解释优先
- 每次状态变化都记录 `reason` 与 `source`
- 指标要能说明“因何提升/下降”

4. 默认安全
- 学习状态仅保存教学相关元数据，不保存敏感隐私
- 审计日志不写明文 token/密码/cookie

---

## 3. 总体架构

### 3.1 三层状态模型

A. 会话热状态（Session Hot State）
- 存储位置：`sessions.supervisor_state`（已有）
- 用途：当前对话轮的快速读写
- 典型字段：
  - `knowledge_graph_position`
  - `emotion_tags`
  - `efficiency_trend`
  - `last_agent_type`
  - `current_problem_context`

B. 用户长期状态（User Learning Profile）
- 新增表：`ai_agent.user_learning_profile`
- 用途：跨会话累计掌握度、薄弱点、学习节奏
- 主键：`user_id`

C. 事件流（Learning Events）
- 新增表：`ai_agent.learning_events`
- 用途：记录状态变化来源（回答、代码提交、情绪变化、建议执行）
- 作为可追溯依据与离线分析输入

### 3.2 数据流（单轮）

1) 用户消息进入 `ws_handler`
2) `process_turn` 完成：路由 -> worker -> 回答 -> knowledge delta
3) 新增步骤：生成学习事件并落库
4) `learning_state_service` 根据事件更新：
   - session hot state（即时）
   - user profile（长期）
5) NextStepSuggester 读取“当前风险标签 + 最新delta”生成更精准建议

---

## 4. 状态指标体系（可落地版本）

### 4.1 核心指标

1) topic_mastery（主题掌握度）
- 范围：[0, 1]
- 来源：知识增量评估 + 题目表现 + 追问质量

2) stability_score（稳定度）
- 范围：[0, 1]
- 含义：掌握是否稳定，是否“学会又忘”
- 依据：近期波动方差、错误反复次数

3) engagement_score（投入度）
- 范围：[0, 1]
- 依据：会话频率、有效交互率、建议执行率

4) frustration_risk（挫败风险）
- 范围：[0, 1]
- 依据：情绪标签、效率下降、连续失败

5) pacing_level（节奏档位）
- 枚举：`slow | normal | fast`
- 依据：`efficiency_trend` + 错误率 + 理解反馈

### 4.2 推荐阈值（首版）

- mastery >= 0.75：可进阶
- 0.45 <= mastery < 0.75：保持当前难度
- mastery < 0.45：回退到基础题型

- frustration_risk >= 0.7：触发“减压+拆步”策略
- stability_score < 0.4：加入“间隔复习”建议

---

## 5. 数据模型设计

### 5.1 新增表一：learning_events

用途：记录每次可解释状态变化。

建议字段：
- `id BIGSERIAL PK`
- `session_id UUID NOT NULL`
- `user_id VARCHAR(64) NOT NULL`
- `event_type VARCHAR(32) NOT NULL`
  - `user_answer`
  - `code_submission`
  - `knowledge_delta`
  - `emotion_update`
  - `suggestion_clicked`
  - `agent_intervention`
- `topic_key VARCHAR(128) NULL`
- `delta_value DOUBLE PRECISION NULL`
- `payload JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

索引建议：
- `(user_id, created_at DESC)`
- `(session_id, created_at DESC)`
- `(event_type, created_at DESC)`

### 5.2 新增表二：user_learning_profile

用途：跨会话长期学习状态。

建议字段：
- `user_id VARCHAR(64) PK`
- `topic_mastery JSONB NOT NULL DEFAULT '{}'`
- `topic_stability JSONB NOT NULL DEFAULT '{}'`
- `engagement_score DOUBLE PRECISION NOT NULL DEFAULT 0.5`
- `frustration_risk DOUBLE PRECISION NOT NULL DEFAULT 0.0`
- `pacing_level VARCHAR(16) NOT NULL DEFAULT 'normal'`
- `weak_topics JSONB NOT NULL DEFAULT '[]'`
- `strong_topics JSONB NOT NULL DEFAULT '[]'`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`

---

## 6. 服务层改造方案

### 6.1 新增服务

1) `app/services/learning_state_service.py`
- 输入：本轮上下文 + 事件列表 + 当前 state
- 输出：更新后的 session state + user profile patch
- 职责：
  - 指标计算
  - 阈值判断
  - 干预标签输出（如 `need_simplify`, `need_review`）

2) `app/repositories/learning_event_repo.py`
- 职责：事件写入/查询

3) `app/repositories/learning_profile_repo.py`
- 职责：用户长期画像 upsert

### 6.2 现有流程插入点

在 `app/services/conversation_orchestrator.py` 的 `process_turn()` 中，位于“知识增量评估后、建议生成前”插入：

- `build_learning_events(...)`
- `learning_event_repo.bulk_create(...)`
- `learning_state_service.apply_events(...)`
- 将返回的 `intervention_flags` 注入 NextStepSuggester 输入

这样可保证建议真正由“学习状态”驱动，而非仅靠文本总结。

---

## 7. 与 Agent 协同策略

### 7.1 Supervisor 路由增强（保持连续性）

在现有 `last_agent_type + message_history` 基础上，加一层状态守卫：
- 若 `frustration_risk >= 0.7`：优先 `learning_partner` 或 `learning_manager`
- 若 `need_review=true`：优先 `learning_manager`
- 若 `current_problem` 且 `mastery<0.45`：`problem_analyzer` 使用“低阶提示模式”

### 7.2 Worker 响应策略参数化

给 worker 增加统一输入字段：
- `teaching_mode`: `explain | scaffold | challenge`
- `pacing_level`: `slow | normal | fast`
- `affective_tone`: `supportive | neutral`

由学习状态服务输出上述参数，避免每个 worker 各自猜测。

---

## 8. 分阶段落地计划

### Phase 1（1~2天）：可追踪化
- 新增 `learning_events` 表与 repo
- 在 `process_turn` 中记录核心事件
- 不改路由与提示策略

验收：每轮对话可看到完整事件链。

### Phase 2（2~3天）：长期画像
- 新增 `user_learning_profile` 表与 upsert 逻辑
- 每轮同步更新长期指标
- 暴露内部调试接口（仅管理员）查看画像

验收：同一用户跨会话状态连续。

### Phase 3（2~3天）：状态驱动干预
- `learning_state_service` 输出 `intervention_flags`
- NextStepSuggester 按 flags 调整建议
- Supervisor 路由引入风险守卫

验收：高风险状态下建议与路由明显更温和、更聚焦。

### Phase 4（可选）：效果评估闭环
- 增加状态质量指标看板
- 验证“建议点击率、完成率、错误回访率”的变化
- 调整阈值与权重

---

## 9. 验证与监控

### 9.1 功能验证
- 单元测试：
  - 指标计算边界（0/1、空事件、异常 payload）
  - profile upsert 幂等
- 集成测试：
  - 一轮对话后 event、session_state、profile 三者一致

### 9.2 运行监控
新增 metrics（Prometheus）：
- `learning_events_total{event_type}`
- `learning_profile_updates_total`
- `learning_interventions_total{flag}`
- `frustration_risk_distribution_bucket`

### 9.3 数据质量守护
- 事件 payload schema 校验（pydantic）
- 定时任务扫描异常值（例如 mastery<0 或 >1）

---

## 10. 风险与应对

1) 指标抖动过大
- 对策：EMA 平滑 + 最小变化阈值（例如 0.05）

2) 过度干预影响体验
- 对策：干预冷却窗口（N轮内不重复触发同类干预）

3) 多连接并发写导致状态覆盖
- 对策：profile 更新采用事务 + 行级锁（`SELECT ... FOR UPDATE`）

4) 事件量增长带来性能压力
- 对策：按月分区或冷热分层；保留聚合快照

---

## 11. 建议实施结论

最合适的落地路径是：
- 先把“状态变化来源”结构化（learning_events）
- 再建立“用户长期学习画像”（user_learning_profile）
- 最后让 Supervisor/Worker/NextStepSuggester 全部受学习状态驱动

该方案与当前 ai-agent-lite 架构兼容，不需要推翻现有流程；同时满足后续“学习路径规划、精准推荐、干预策略评估”的扩展需求。

---

## 12. OJ 提交记录与 AI 打通（关键补充）

你指出的是最关键链路：
“学生在 OJ 的真实提交行为”必须自动进入 AI 学习状态，而不是依赖手工“发给AI”。

### 12.1 当前已具备能力（代码现状）

1) 前端已拿到真实提交结果
- `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
  - `submitSolution()` 调 `POST /oj-api/api/submission`
  - 基于 `submission_id` 轮询 `GET /oj-api/api/submissions`
  - 结束后拉 `GET /oj-api/api/submission?id=...` 获取详情

2) 前端可把“代码 + 结果”作为附件发到聊天
- `frontend-vue-ai-chat/src/composables/useChatFeature.js`（`pendingAttachments`）
- 但这是“用户主动触发”，不是系统自动打通

3) AI 侧已能读取 submission 细节与测试点内容
- `ai-agent-lite/app/routers/oj_test_cases.py`
  - 通过 DB 直接查 `submission` 表（`result/statistic_info/info`）
  - 结合 test_case 文件返回 input/expected/output

=> 结论：
“读取能力”已有；缺的是“自动事件桥接 + 状态入模”。

### 12.2 目标链路（必须实现）

OJ 判题完成 -> 产生 submission 事件 -> ai-agent-lite 接收 -> 标准化 -> 写入 learning_events -> 更新 user_learning_profile/session_state -> 触发下一轮建议与干预

### 12.3 推荐方案：事件驱动双通道

A. 主通道（推荐）：OJ Webhook 推送到 ai-agent-lite
- 新增 OJ 侧 webhook（判题完成时触发）
- ai-agent-lite 新增 `POST /oj/submission_event` 接口接收
- 优点：低延迟、无需轮询、可全量覆盖“未发给AI”的提交

B. 兜底通道：前端提交结束后上报
- 前端在拿到最终 submission 详情后，再调用 ai-agent-lite 内部接口上报
- 优点：改动快；缺点：只覆盖前端在线场景

建议：先上 B 快速闭环，再上 A 做生产级可靠。

### 12.4 事件模型（入 learning_events）

新增事件类型（至少）：
- `oj_submission_judged`
- `oj_submission_failed`
- `oj_submission_accepted`
- `oj_submission_compile_error`

`payload` 推荐字段：
- `submission_id`
- `problem_id`（数值）
- `problem_display_id`（如 fps-xxxx）
- `user_id`
- `language`
- `result_code`（JudgeStatus）
- `result_label`
- `score`
- `time_cost`
- `memory_cost`
- `error_type`（CE/WA/TLE/RE/MLE/...）
- `failed_test_case_index`
- `test_case_summary`（pass/total）
- `source`（webhook/frontend_fb）

### 12.5 状态映射规则（把判题变成学习状态）

1) topic_mastery
- AC：该题关联 topic +0.03~0.08
- WA/TLE/RE：关联 topic -0.01~0.03（按连续失败次数递增惩罚）

2) frustration_risk
- CE/连续 WA/TLE 时上升
- AC 且耗时下降时下降

3) pacing_level
- 高频失败 + 长时间无 AC -> `slow`
- 连续 AC + 低耗时 -> `fast`

4) intervention_flags
- `need_compile_help`（CE）
- `need_complexity_hint`（TLE）
- `need_edge_case_training`（WA 在后半测试点）
- `need_runtime_safety`（RE）

### 12.6 代码落点（本仓库）

新增：
- `ai-agent-lite/app/routers/oj_submission_event.py`
- `ai-agent-lite/app/services/oj_submission_ingest_service.py`
- `ai-agent-lite/app/services/submission_to_learning_mapper.py`

修改：
- `ai-agent-lite/app/main.py`
  - `app.include_router(oj_submission_event.router)`
- `ai-agent-lite/app/services/learning_state_service.py`
  - 增加 `apply_submission_event(...)`
- `ai-agent-lite/app/repositories/learning_event_repo.py`
  - 增加 submission 事件批量入库接口

前端（兜底通道）：
- `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
  - 在 `submitSolution()` 判题终态后调用 ai-agent-lite 上报接口

### 12.7 接口草案

1) OJ -> AI（webhook）
- `POST /oj/submission_event`
- Header: `X-OJ-Signature`（HMAC）
- Body:
  - `submission_id`, `user_id`, `problem_id`, `result`, `statistic_info`, `info`, `judged_at`

2) 前端 -> AI（fallback）
- `POST /oj/submission_event/fallback`
- Body 与上面一致，但 `source=frontend_fb`

幂等键：`submission_id + result`
- 已处理则直接 200（避免重复写入）

### 12.8 安全与一致性

1) webhook 验签（HMAC-SHA256）
2) 仅允许内网/可信源访问 webhook
3) payload schema 校验 + 字段白名单
4) 幂等表或唯一索引，防止重复消费
5) 事件处理失败进入 dead-letter（或重试队列）

### 12.9 验收标准（这部分必须加到联调）

1) 学生只在 OJ 提交，不点“发给AI”，AI 画像仍能在下一轮体现变化
2) CE/WA/TLE/AC 四类提交都能产出对应 `learning_events`
3) 同一 submission 重放不会重复计分（幂等通过）
4) NextStepSuggester 能根据 submission 失败类型给出不同建议
5) `user_learning_profile` 在跨会话后仍保留该变化

---

## 13. 本仓库建议新增/修改文件清单

新增：
- `ai-agent-lite/app/services/learning_state_service.py`
- `ai-agent-lite/app/repositories/learning_event_repo.py`
- `ai-agent-lite/app/repositories/learning_profile_repo.py`
- `ai-agent-lite/app/models/learning_state.py`（可选，事件与画像 dataclass）
- `ai-agent-lite/app/routers/oj_submission_event.py`
- `ai-agent-lite/app/services/oj_submission_ingest_service.py`
- `ai-agent-lite/app/services/submission_to_learning_mapper.py`
- `ai-agent-lite/alembic/versions/<timestamp>_add_learning_state_tables.py`

修改：
- `ai-agent-lite/app/main.py`（注册 submission_event router）
- `ai-agent-lite/app/services/conversation_orchestrator.py`
- `ai-agent-lite/app/services/state_manager.py`（仅补充集成入口，保持职责清晰）
- `ai-agent-lite/app/metrics.py`（新增学习状态指标）
- `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`（提交终态 fallback 上报）

文档：
- `docs/plans/student-learning-state-management-solution.md`（本文）

---

## 14. 用户新增要求（已记录）

以下 4 项作为强约束纳入方案：

1) 去掉“发给AI”按钮，改为自动发送
- 前端提交后，系统自动把“代码 + 精简后的判题结果”发送给 AI。
- 交互上不再要求学生手工点击“发给AI”。

2) Agent 在对话过程中持续分析掌握度
- 每轮对话都更新知识点掌握度与风险标签。
- 对话结束时产出结构化建议（复习/巩固/进阶）。

3) 一题完成后立即推荐后续未完成题
- 优先推荐同类未完成题做巩固。
- 若同类题已熟练，自动提升到更深知识点或更高难度题目。

4) 题库知识点标注
- 为题目建立可计算的知识点标签体系。
- 推荐、掌握度更新、学习路径都基于同一套标签。

---

## 15. 针对 4 项要求的落地补充

### 15.1 自动发送链路（替代“发给AI”按钮）

前端改造：
- 删除按钮：`frontend-vue-ai-chat/src/App.vue` 中 `handleSubmitCodeToAi` 入口。
- 在 `submitSolution()` 判题终态（AC/WA/CE/TLE/RE/MLE 等）后自动调用：
  - `sendSubmissionToAi({ code, summarized_result, submission_id, problem_context })`
- 保留开关（默认开启）：`AUTO_SEND_SUBMISSION_TO_AI=true`，便于灰度。

后端改造（ai-agent-lite）：
- 新增 `POST /oj/submission_event/fallback` 接口接收自动上报。
- 统一进入 `oj_submission_ingest_service`，写入 learning_events 并触发状态更新。

### 15.2 判题结果“简洁化”标准（发送给 AI 的内容）

不要把完整 test case 大对象直接塞给对话上下文，改为“摘要 + 必要明细”：

摘要字段（必需）：
- `submission_id`
- `result_label`（AC/WA/CE/TLE/RE/MLE）
- `pass_ratio`（例如 7/10）
- `first_failed_case`（例如 #8）
- `time_cost_ms`
- `memory_kb`
- `key_error`（CE/RE 时截断后的核心错误，建议 <= 300 chars）

仅在失败时附加：
- `failed_case_compact`：最多 1~2 个失败点（输入摘要、期望/实际差异摘要）

这样既保留诊断信息，又控制 token 开销与噪声。

### 15.3 对话期掌握度分析与建议生成

在 `process_turn()` 中固定执行：
1. `KnowledgeAssessor.assess(...)`（已有）
2. `learning_state_service.apply_events(...)`（新增）
3. 输出 `intervention_flags`
4. `NextStepSuggester` 基于 `state_delta + intervention_flags` 生成建议

建议输出结构保持简洁：
- `keep_doing`（继续做什么）
- `fix_now`（当前最该修正点）
- `next_problem_type`（下一题类型）

### 15.4 完题后推荐策略（未完成优先 + 熟练进阶）

新增推荐服务：`problem_recommendation_service.py`

输入：
- 当前题结果（是否 AC、尝试次数、耗时）
- 用户画像（topic_mastery/topic_stability/frustration_risk）
- 题库标签（topic/difficulty/prerequisite）

策略：
1. 若当前 topic 未达熟练阈值（如 mastery < 0.75）：
   - 推荐同 topic 未完成题（难度相近）
2. 若达到熟练阈值且稳定度高（如 stability >= 0.6）：
   - 推荐同 topic 更高难度题
   - 或推荐下游知识点题目（按 prerequisite 图）
3. 若挫败风险高：
   - 推荐回退一档难度并给微目标

### 15.5 题库知识点标注方案

数据层新增：
- `problem_topic_tags(problem_id, topic_key, weight, source, version)`
- `topic_graph(topic_key, parent_topic, prerequisite_topic, difficulty_level)`

标注来源：
1. 人工基线标签（教研可控）
2. LLM 辅助标注（批处理）
3. 线上纠偏（根据提交行为与教师反馈修正）

治理规则：
- 每题至少 1 个主标签（weight 最高）
- 标签版本化（便于回滚）
- 周期性抽样复核

---

## 16. 实施优先级（按你当前诉求）

P0（先做）
1. 移除“发给AI”按钮 + 提交终态自动发送
2. 判题结果摘要化（压缩到简洁结构）
3. submission 事件入 learning_events（幂等）

P1（紧接）
4. 完题后即时推荐（未完成优先）
5. 熟练后进阶推荐（难度/知识点升级）

P2（并行推进）
6. 全量题库知识点标注与 topic_graph 建设

---

## 17. 增补文件清单（相对第 13 节）

额外新增：
- `ai-agent-lite/app/services/problem_recommendation_service.py`
- `ai-agent-lite/app/services/submission_result_summarizer.py`
- `ai-agent-lite/alembic/versions/<timestamp>_add_problem_topic_tags.py`
- `ai-agent-lite/alembic/versions/<timestamp>_add_topic_graph.py`

额外修改：
- `frontend-vue-ai-chat/src/App.vue`（移除“发给AI”按钮）
- `frontend-vue-ai-chat/src/composables/useChatFeature.js`（移除手工附件触发路径）
- `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`（提交终态自动发送）
- `ai-agent-lite/app/services/conversation_orchestrator.py`（接入推荐服务）
- `ai-agent-lite/app/repositories/*`（题目标签与推荐查询）

---

## 18. 方案复审结果（遗漏点与改进项）

本节为本次复审新增，结论：当前方案方向正确，但还缺 10 个关键落地点。

### 18.1 P0 级遗漏（必须先补）

1) “自动发送给 AI”与“仅写事件”边界未明确
- 现方案里 fallback 更偏“入学习状态”，但用户诉求是“自动发送给 AI 并分析”。
- 必须明确两条并行动作：
  - A. 写 `learning_events`（结构化状态）
  - B. 触发一次 AI 分析输入（可作为 system event message 或异步 analysis task）

2) 会话绑定缺失（submission -> AI session）
- 需增加 `ai_session_id` 或 `conversation_id` 关联字段，避免“状态更新到用户但没进当前会话”。
- 建议在前端上报时携带：`session_id/user_id/problem_id/submission_id` 四元组。

3) “题目完成”的判定规则未定义
- 推荐逻辑依赖“完成一题后”，必须定义：
  - 默认：`first_ac` 才触发“完成”
  - `rejudge` 不重复触发完成事件
  - 已 AC 后再次提交仅更新熟练度，不再创建 completion 事件

4) 幂等维度不够
- 当前写 `submission_id + result`，但判题系统可能 rejudge 同 result 不同 detail。
- 建议幂等键改为：`submission_id + judge_version + result + score + time_cost + memory_cost`（或 payload hash）。

### 18.2 P1 级改进（强烈建议）

5) 自动发送的延迟与失败补偿未定义
- 需要异步队列化，避免阻塞提交 UI。
- 增加重试策略（指数退避）和 dead-letter 表。

6) 结果摘要规范需增加“长度上限 + 脱敏”
- 建议统一限制：
  - `key_error <= 300 chars`
  - `failed_case_compact <= 2 cases`
  - 总摘要 <= 1.5KB
- 对编译器路径、系统路径、内部 IP 做脱敏。

7) 推荐策略缺少“来源约束”
- 需要明确排除：
  - contest 进行中题目
  - teacher hidden/private 题目
  - 无权限题目
- 推荐查询必须带用户可见性过滤。

8) 题库标签未定义“标签置信度与冲突处理”
- 增加字段：`confidence`、`review_status`、`reviewed_by`。
- 当 LLM 标签与人工标签冲突时，人工优先并写审计记录。

### 18.3 P2 级完善（上线后优化）

9) 掌握度模型缺少“遗忘曲线”
- 当前只看增减，建议加入时间衰减（Ebbinghaus-like decay），防止“旧 AC 永久高分”。

10) 观测指标不完整
- 增加业务指标：
  - 自动发送成功率
  - submission->AI 分析延迟 P50/P95
  - 推荐点击率、推荐后 AC 转化率
  - 错误类型分布（CE/WA/TLE/RE）随时间变化

---

## 19. 必改补丁清单（按实施顺序）

1) 数据模型补充
- `learning_events` 增加：`ai_session_id`, `idempotency_key`, `source_event_time`
- 新增：`learning_event_dlq`（失败事件）

2) 接口补充
- `POST /oj/submission_event/fallback` 请求体强制包含：
  - `session_id`, `user_id`, `problem_id`, `submission_id`, `result_summary`
- 返回：`accepted=true`, `event_id`, `analysis_task_id`

3) 服务补充
- `oj_submission_ingest_service`：事件落库 + 幂等检查 + 异步投递分析任务
- `submission_result_summarizer`：统一摘要与脱敏
- `problem_recommendation_service`：权限过滤 + 完题触发推荐

4) 前端补充
- 移除“发给AI”按钮后，提交成功自动触发两步：
  - 上报 fallback 事件
  - 在当前会话插入一条系统提示（简洁结果摘要）供用户可见

5) 验收补充
- 新增 6 条 E2E：
  - 自动发送成功/失败重试
  - rejudge 幂等
  - first_ac 触发推荐
  - 推荐权限过滤
  - 无手工点击也能更新掌握度
  - 会话内可见 AI 对本次提交的分析回执

---

## 20. 实施进展（2026-04-27）

已完成（P0 第一批可运行改造）：

1) ai-agent-lite 新增 fallback 接口与事件入库
- 新增路由：`POST /oj/submission-events/fallback`
- 文件：`ai-agent-lite/app/routers/submission_events.py`
- 能力：
  - 校验终态提交状态（AC/WA/CE/TLE/RE 等）
  - 校验 `session_id` UUID 格式
  - 生成标准摘要并持久化
  - 返回幂等结果（`created=true/false`）

2) 新增 submission 事件表模型（幂等约束）
- 文件：`ai-agent-lite/app/models/orm.py`
- 新模型：`SubmissionEvent`
- 幂等键：`(submission_id, event_type, event_version)` 唯一约束
- 关键字段：`session_id/user_id/problem_id/status/summary/raw_payload/should_trigger_ai`

3) 新增仓储层与摘要器
- 文件：
  - `ai-agent-lite/app/repositories/submission_event_repo.py`
  - `ai-agent-lite/app/services/submission_summary.py`
- 能力：
  - 幂等插入（冲突回查既有行）
  - 摘要统一格式、限长、基础脱敏（手机号/邮箱）
  - 统计 `test_cases_total/test_cases_passed`

4) 前端移除“发给AI”按钮并改为提交终态自动发送
- 文件：`frontend-vue-ai-chat/src/App.vue`
- 改造：
  - 删除 `handleSubmitCodeToAi` 及按钮
  - `handleSubmitCode` 在判题终态后自动：
    - 上报 fallback 事件
    - 将代码+结果打包为附件
    - 直接调用 `sendMessage()` 自动发给 AI

5) 前端 API 客户端新增 fallback 上报
- 文件：
  - `frontend-vue-ai-chat/src/services/apiClient.js`
  - `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
- 新方法：`reportSubmissionFallback(payload)`
- 支持环境变量：
  - `VITE_OJ_API_BASE_URL`（默认 `/oj-api`）
  - `VITE_AGENT_API_BASE_URL`（默认 `/oj-test-cases`）

6) 主应用注册新路由
- 文件：`ai-agent-lite/app/main.py`
- 已 include：`submission_events.router`

7) fallback 入库链路增强（P0 第二批）
- 文件：
  - `ai-agent-lite/app/routers/submission_events.py`
  - `ai-agent-lite/app/repositories/session_repo.py`
- 改造：
  - 当 `session_id` 缺失时，按 `user_id + problem_id + active + 最近更新时间窗口` 自动回补 session 绑定
  - 审计明细增加 `session_bound` 标识，便于观测绑定命中率

8) first_ac 推荐链路健壮性增强（P0 第二批）
- 文件：`ai-agent-lite/app/routers/submission_events.py`
- 改造：
  - 推荐逻辑仅在 `created && is_first_ac` 下触发
  - 推荐服务异常隔离为 warning，不影响 fallback 主链路成功返回

9) dead-letter 重试通道落地（P0 第二批）
- 文件：
  - `ai-agent-lite/app/routers/submission_events.py`
  - `ai-agent-lite/app/repositories/submission_event_repo.py`
- 新增：
  - `POST /oj/submission-events/retry-dlq`
  - `list_pending_dlq / mark_dlq_resolved / increment_dlq_retry`
- 作用：
  - 对 unresolved DLQ 事件按批次重放
  - 成功后标记 resolved，失败则增加 retry_count 并刷新 error_message

10) 补偿链路服务化与定时化（P0 第二批增补）
- 文件：
  - `ai-agent-lite/app/services/submission_dlq_replay.py`
  - `ai-agent-lite/app/tasks/submission_events.py`
  - `ai-agent-lite/app/celery_app.py`
  - `ai-agent-lite/app/routers/problem_audit.py`
- 新增能力：
  - 抽出 `replay_submission_dlq()` 复用在 API 与 Celery task
  - 新增 Celery 任务 `app.tasks.submission_events.retry_submission_dlq`
  - Beat 每 5 分钟自动触发 DLQ replay（limit=20）
  - 新增手动触发入口 `POST /audit/submission/retry-dlq?limit=20`

11) 补偿链路监控指标（P1）
- 文件：
  - `ai-agent-lite/app/metrics.py`
  - `ai-agent-lite/app/services/submission_dlq_replay.py`
  - `ai-agent-lite/app/routers/submission_events.py`
  - `ai-agent-lite/app/tasks/submission_events.py`
  - `ai-agent-lite/app/repositories/submission_event_repo.py`
- 新增指标：
  - `submission_fallback_events_total{outcome,status_label,source}`
  - `submission_dlq_replay_runs_total{outcome}`
  - `submission_dlq_replay_rows_total{outcome}`
  - `submission_dlq_replay_duration_seconds`
  - `submission_dlq_pending_rows`
- 监控语义：
  - fallback created/duplicate/failed 全链路可观测
  - DLQ replay 的成功率、失败量、耗时、积压量可直接通过 Prometheus 抓取

当前未完成（下一步）：
- 完整 E2E 用例（文档第19节定义）
- 推荐策略升级为知识点/难度多目标（当前为可用兜底版）

12) 告警规则草案落地（P1）
- 文件：
  - `docs/monitoring/ai-agent-lite-alert-rules.yml`
  - `docs/monitoring/prometheus.yml`
- 新增规则：
  - `SubmissionFallbackFailureSpike`：15 分钟失败占比 >20% 且失败数>=5
  - `SubmissionDlqReplayFailureRatioHigh`：15 分钟 replay 失败占比 >30% 且失败行>=3
  - `SubmissionDlqPendingBacklogHigh`：DLQ 积压 >50 且持续 15 分钟
  - `SubmissionDlqReplayLatencyP95High`：replay p95 耗时 >5s 持续 10 分钟
  - `SubmissionFallbackIngestStalledWithBacklog`：有积压但 30 分钟无 created
- 说明：
  - 已提供最小 Prometheus 抓取配置（job: `ai-agent-lite`）
  - 阈值按当前系统负载估算，建议上线后一周依据实际流量回调

验证记录：
- 前端构建：`npm run build` 通过
- Python 语法解析：新增后端文件 AST 解析通过
- 本地无法执行 FastAPI 运行态导入验证（环境缺少 fastapi 依赖）
- 新增 E2E 冒烟脚本：`ai-agent-lite/scripts/test_submission_fallback_e2e.py`
  - 覆盖：自动发送成功路径、rejudge 幂等、first_ac 信号、DLQ replay API
  - 实测：`python scripts/test_submission_fallback_e2e.py` 全部 3/3 通过（容器重建后）

13) 一致性修复（P0）
- 问题：`source='frontend_fallback'` 长度 17 超出后端 `max_length=16`，导致 fallback 422
- 修复：统一 source 值为 `frontend_fb`（长度 11）
- 修改文件：
  - `ai-agent-lite/app/routers/submission_events.py`
  - `ai-agent-lite/app/models/orm.py`
  - `ai-agent-lite/app/services/submission_dlq_replay.py`
  - `frontend-vue-ai-chat/src/composables/useOjAuthAndProblems.js`
  - `ai-agent-lite/scripts/test_submission_fallback_e2e.py`
- 验证：
  - `POST /oj/submission-events/fallback` 返回 200
  - `POST /oj/submission-events/retry-dlq` 返回 200
  - OpenAPI 已包含 submission-events 路由

14) 监控栈接入与在线验证（P1）
- 新增 root compose 服务：`prometheus`（端口 `9090`）
- 修改文件：`docker-compose.yml`
- 验证结果：
  - `http://127.0.0.1:9090/-/ready` 返回 200
  - `api/v1/rules` 已加载 `ai-agent-lite-submission-fallback` 规则组
  - `api/v1/targets` 显示 `job=ai-agent-lite` 且 `health=up`
  - 指标查询返回非空：
    - `submission_fallback_events_total`（3 条序列）
    - `submission_dlq_pending_rows`（1 条序列）
    - `submission_dlq_replay_runs_total`（1 条序列）
- 注意：
  - 已修复宿主目录权限并切回持久化存储：`./data/prometheus:/prometheus`
  - 当前 `--storage.tsdb.path=/prometheus`，容器重启后数据可保留

15) 监控容器停用（当前环境）
- 修改文件：`docker-compose.yml`
- 处理：
  - 已将 `prometheus` 服务整段注释，默认不随 compose 启动
  - 已停止并删除运行中的容器 `cdut-prometheus`
- 当前状态：
  - 监控配置文件保留：
    - `docs/monitoring/prometheus.yml`
    - `docs/monitoring/ai-agent-lite-alert-rules.yml`
  - 监控能力处于“代码保留、运行停用”状态
- 恢复方式（需要时）：
  - 取消 `docker-compose.yml` 中 `prometheus` 段注释
  - 执行：`docker compose up -d prometheus`
