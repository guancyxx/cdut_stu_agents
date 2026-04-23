# AI Agent 架构分析

**分析日期**: 2026-04-23
**目标服务**: ai-agent-lite (FastAPI + Supervisor 模式)

## 代码规模

| 模块 | 行数 | 职责 |
|------|------|------|
| main.py | 329 | FastAPI 入口 + WS handler + 流式发送 |
| workers.py | 220 | 5 个专业 Worker Agent |
| supervisor.py | 179 | 中央路由器 + 意图分类 + 情感分析 |
| llm_client.py | 146 | LLM 调用（含重试/流式/降级） |
| state_manager.py | 85 | 学生状态持久化 |
| models.py | 63 | ORM 模型 (Session/Message/AuditLog) |
| message_repo.py | 63 | 消息 CRUD |
| session_repo.py | 60 | 会话 CRUD |
| database.py | 47 | 连接池 + schema 初始化 |
| audit.py | 46 | 审计日志 |
| metrics.py | 30 | Prometheus 指标 |
| middleware.py | 23 | 请求中间件 |
| **合计** | **1325** | |

## 当前运行状态

- 所有容器正常运行 (docker compose ps)
- healthz: `{"ok":true,"llm_enabled":true,"model":"deepseek-chat"}`
- readyz: `{"ok":true,"db":true,"llm":true,"model":"deepseek-chat"}`
- LLM 后端: DeepSeek Chat (api.deepseek.com)

## 请求处理流程

1. 前端发送 `{"type":"query","content":{"query":"..."}}`
2. main.py 接收 → 持久化用户消息到 DB
3. Supervisor.route_request() 执行意图分类 (LLM 调用 #1)
4. 路由到 5 个 Worker 之一
5. Worker.process() 调用 LLM 生成响应 (LLM 调用 #2)
6. ~~Supervisor.get_next_actions() 生成下一步建议 (LLM 调用 #3)~~ → **已移除**
7. 通过 WS 分块发送响应
8. 持久化 assistant 消息到 DB

## 已识别问题

> 完整优化待办见 `specs/001-ai-tutor/spec.md` — Optimization Backlog

### P0 — 关键性能与正确性

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| OPT-001 | 每次请求多次 LLM 调用（已移除 NextStepSuggester 降为 2 次） | 2x 延迟+成本 | NextStepSuggester 已移除；意图分类合并待实现 |
| OPT-002 | Worker 使用 complete() 而非 stream() | 用户等待完整生成才可见内容 | 待实现 |
| OPT-003 | main.py _load_context() 重复定义（第 117 行和第 123 行） | 潜在 Bug | 待修复 |

### P1 — 缺失的守卫与模块

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| OPT-004 | 无范围守卫 (tutor_policy.py) | 非编程查询浪费 LLM token | 待实现 |
| OPT-005 | 无边界路由器 (boundary_router.py) | 路由粒度粗糙 | 待实现 |
| OPT-006 | 无响应格式化器 (response_formatter.py) | 输出无结构保证 | 待实现 |

### P2 — 架构与健壮性

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| OPT-007 | Supervisor 每次 WS 连接重新实例化 | 状态不共享 | 待优化 |
| OPT-008 | StateManager 无并发保护 | 多连接写同一 session 可能丢失 | 待优化 |
| OPT-009 | 情感分析仅关键词匹配 | 误判风险 | 待改进 |
| OPT-010 | 无在线检索 (web_retrieval.py) | 无法引用外部文档 | 待实现 |

### P3 — 优化与监控

| 编号 | 问题 | 影响 | 状态 |
|------|------|------|------|
| OPT-011 | 前端冗余正则 Agent 识别 | 死代码，可能误识别 | 待清理 |
| OPT-012 | LLM 调用耗时未计入 metrics | 无法测量实际延迟 | 待实现 |
| OPT-013 | 无用户级限流 | 滥用风险 | 待实现 |

## Spec 完成度对照

| Spec 需求 | 状态 | 备注 |
|-----------|------|------|
| 基础 Q&A | Done | — |
| 代码片段输入 | Done | — |
| OJ 问题集成 | Done | — |
| OJ 代码提交 | Done | — |
| 持久化会话存储 | Not yet | DB 表就绪，恢复逻辑不完整 |
| 用户身份绑定 | Not yet | DB 字段存在，前端绑定不完整 |
| 代码审查结构化 | Not yet | response_formatter.py |
| 学习进度追踪 | Not yet | state_manager 基础在，无分析 |
| 错误调试辅助 | Partial | 无结构化 debug 流程 |
| 范围守卫 | Not yet | tutor_policy.py + boundary_router.py |
| 在线检索 | Not yet | web_retrieval.py |
| 流式响应 | Not yet | stream() API 已实现但 Worker 未调用 |

## 优化建议优先级

| 优先级 | 改进项 | 预期收益 |
|--------|--------|----------|
| P0 | 合并意图分类到 Worker 调用（1 次 LLM/请求） | 延迟再降 50%，成本降 50% |
| P0 | 启用流式响应 llm.stream() | 用户感知延迟大幅降低 |
| P0 | 修复重复 _load_context() 定义 | 消除潜在 Bug |
| P1 | 实现 tutor_policy.py 范围守卫 | 防止非编程查询消耗资源 |
| P1 | 实现 boundary_router.py 边界路由 | 细粒度路由+自动检索决策 |
| P2 | 实现 response_formatter.py 结构化输出 | 代码审查质量提升 |
| P2 | 实现 web_retrieval.py 在线检索 | 答案时效性和准确性 |
| P2 | Supervisor 单例化 + StateManager 并发保护 | 多连接一致性 |

## 变更日志

| 日期 | 变更 |
|------|------|
| 2026-04-23 | 初始架构分析。移除 NextStepSuggester。记录 OPT-001 至 OPT-013。标注中文唯一语言策略。 |
