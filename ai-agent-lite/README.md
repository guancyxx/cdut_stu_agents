# ai-agent-lite

轻量级 FastAPI AI 代理，驱动 CDUT 学生竞赛培训系统。采用 Supervisor 模式与专业化 Worker Agent，通过 WebSocket 流式输出 LLM 响应，兼容 frontend-vue-ai-chat 可组合协议。

**界面语言**：简体中文为唯一交互语言。所有面向用户的提示词、响应、Agent 名称和描述均为中文。

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                   Supervisor 模式                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  用户输入 → Supervisor → 智能路由 → Worker                   │
│                                                              │
│  ┌──────────┐   ┌─────────────────┐   ┌────────────────┐    │
│  │          │   │                 │   │                │    │
│  │  输入    │──►│   Supervisor     │──►│  CodeReviewer  │    │
│  │          │   │  (意图分类+路由)  │   │                │    │
│  └──────────┘   └─────────────────┘   └────────────────┘    │
│                       │   ┌────────────────┐                │
│                       │   │ProblemAnalyzer │                │
│                       │   └────────────────┘                │
│                       │   ┌────────────────┐                │
│                       └──►│  ContestCoach   │                │
│                           └────────────────┘                │
│                       ┌────────────────┐                    │
│                       │LearningPartner │                    │
│                       └────────────────┘                    │
│                       ┌────────────────┐                    │
│                       │LearningManager │                    │
│                       └────────────────┘                    │
└──────────────────────────────────────────────────────────────┘
```

> **注意**：NextStepSuggester（每轮对话末尾的"下一步建议"生成器）已移除。该组件每次请求额外调用一次 LLM，导致 3x 调用开销。见优化待办 OPT-001。

## Worker Agent 列表

1. **代码审查专家** (CodeReviewer) — 代码质量、效率和风格评估
2. **问题解析专家** (ProblemAnalyzer) — 算法解释和问题拆解
3. **竞赛教练** (ContestCoach) — 竞赛策略和表现优化
4. **学习伙伴** (LearningPartner) — 情感支持和学习动力
5. **学习管理专家** (LearningManager) — 个性化学习路径推荐

## 已知问题与优化待办

> 详见 `specs/001-ai-tutor/spec.md` 的 Optimization Backlog 章节。

### 关键问题

| 优先级 | 编号 | 问题 | 当前影响 |
|--------|------|------|----------|
| P0 | OPT-001 | 每次请求 3 次 LLM 调用（已移除 NextStepSuggester 降为 2 次，意图分类合并待实现） | 2x 延迟+成本 |
| P0 | OPT-002 | Worker 使用 complete() 而非 stream() | 用户需等待完整生成才能看到内容 |
| P0 | OPT-003 | main.py _load_context() 重复定义 | 潜在 Bug |
| P1 | OPT-004 | 无范围守卫（tutor_policy.py 未实现） | 非编程查询浪费 LLM token |
| P1 | OPT-005 | 无边界路由器（boundary_router.py 未实现） | 路由粒度粗糙 |
| P1 | OPT-006 | 无响应格式化器（response_formatter.py 未实现） | 输出无结构保证 |
| P2 | OPT-007 | Supervisor 每次 WS 连接重新实例化 | 状态不共享 |
| P2 | OPT-008 | StateManager 无并发保护 | 多连接写同一 session 可能丢失 |
| P2 | OPT-009 | 情感分析仅关键词匹配 | 误判风险 |
| P2 | OPT-010 | 无在线检索（web_retrieval.py 未实现） | 无法引用外部文档 |

### 未实现模块

以下模块在 Skill 文档中有设计但尚未创建：

- `app/boundary_router.py` — LLM 边界路由（scope + need_retrieval + answer_mode）
- `app/tutor_policy.py` — 教学策略/范围守卫
- `app/web_retrieval.py` — 在线检索适配器
- `app/response_formatter.py` — 结构化输出格式化

## 快速开始 (Docker)

```bash
# 在项目根目录（使用 docker-compose）
docker compose up -d ai-agent-lite

# 健康检查（宿主机端口 8850 -> 容器内 8848）
curl http://127.0.0.1:8850/healthz
```

## 快速开始 (本地)

```bash
pip install -r requirements.txt
LITE_LLM_BASE_URL=https://api.deepseek.com/v1 \
LITE_LLM_API_KEY=your-key \
LITE_LLM_MODEL=deepseek-chat \
uvicorn app.main:app --port 8848
```

## 端点

### HTTP
- `GET /healthz` — 存活检查。返回 `{"ok":true,"llm_enabled":bool,"model":"..."}`
- `GET /readyz` — 就绪检查（DB + LLM 依赖验证）
- `GET /metrics` — Prometheus 指标端点

### WebSocket
- `WS /ws?session_id={sessionId}&user_id={userId}` — 聊天端点
  - `session_id` 可选。无效/缺失时服务器创建新 UUID 会话。
  - `user_id` 可选。默认 `anonymous`。

## WebSocket 协议

### 客户端 -> 服务端

```json
{"type": "query", "content": {"query": "用户消息文本"}}
```

可选：
```json
{"type": "list_agents"}
```

### 服务端 -> 客户端

初始化：
```json
{"type":"init","data":{"type":"init","default_agent":"ai-agent-lite","agent_type":"supervisor","sub_agents":["code_reviewer","problem_analyzer","contest_coach","learning_partner","learning_manager"],"session_id":"<uuid>"}}
```

Agent 信息（在响应前发送）：
```json
{"type":"agent_info","data":{"agent_type":"code_reviewer","agent_name":"代码审查专家","agent_description":"专注于代码质量、效率和风格评估，提供优化建议","agent_icon":"💻","agent_color":"#5a9fd4"}}
```

流式文本：
```json
{"type":"raw","data":{"type":"text","delta":"token文本","inprogress":true}}
```

结束：
```json
{"type":"finish"}
```

错误：
```json
{"type":"error","data":{"type":"error","code":"INVALID_INPUT","message":"错误描述"}}
```

> ~~Next-step suggestions~~ 已移除。不再发送 `next_suggestions` 类型消息。

## 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| LITE_LLM_BASE_URL | 否 | - | OpenAI 兼容 API 基础 URL |
| LITE_LLM_API_KEY | 否 | - | LLM 提供商 API Key |
| LITE_LLM_MODEL | 否 | deepseek-chat | 模型名称 |
| LITE_LLM_TIMEOUT | 否 | 30 | 请求超时（秒） |
| OJ_API_URL | 否 | - | QDUOJ 后端 URL（OJ 集成用） |
| LITE_DATABASE_URL | 否 | postgresql+asyncpg://... | PostgreSQL 连接串 |
| LITE_DB_SCHEMA | 否 | ai_agent | 数据库 schema 名 |

当 LITE_LLM_BASE_URL + LITE_LLM_API_KEY 均设置时，LLM 启用。
否则 Agent 以模拟模式运行（回显响应）。

在 docker-compose 中，这些变量映射自 .env 的 UTU_LLM_* 变量：
- LITE_LLM_BASE_URL=${UTU_LLM_BASE_URL}
- LITE_LLM_API_KEY=${UTU_LLM_API_KEY}
- LITE_LLM_MODEL=${UTU_LLM_MODEL}

## 会话存储

当前：PostgreSQL 持久化存储，使用 `ai_agent` schema。

数据表：
- `ai_agent.sessions` — 会话元数据 + Supervisor 状态
- `ai_agent.messages` — 用户/助手消息
- `ai_agent.audit_log` — 审计日志

`LITE_DATABASE_URL` 默认指向共享 QDUOJ PostgreSQL 容器 (`oj-postgres`)，通过 schema 逻辑隔离。

## 端口映射

| 范围 | 端口 |
|------|------|
| 容器内部 | 8848 |
| 宿主机 (docker-compose) | 8850 |
| 前端 WS 代理目标 | ws://ai-agent-lite:8848 |

## 架构图

```
frontend-vue-ai-chat
        |
        | WS /ws?session_id=X
        v
ai-agent-lite (FastAPI + Supervisor 模式)
  ├── Supervisor (意图分类 + 智能路由 + 状态管理)
  ├── CodeReviewer (代码审查和优化建议)
  ├── ProblemAnalyzer (算法问题分析)
  ├── ContestCoach (竞赛策略指导)
  ├── LearningPartner (学习陪伴和情感支持)
  ├── LearningManager (个性化学习管理)
  └── StateManager (学生状态持久化)
        |
        | HTTP /chat/completions
        v
LLM Provider (DeepSeek)
```

## 配置

Supervisor 模式可通过环境变量配置：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| SUPERVISOR_ENABLED | 否 | true | 启用 Supervisor 模式路由 |
| MAX_CONTEXT_MESSAGES | 否 | 20 | 上下文历史消息数 |
| STATE_PERSISTENCE_INTERVAL | 否 | 60 | 状态持久化间隔（秒） |
| EMOTION_ANALYSIS_ENABLED | 否 | true | 启用情感感知路由 |

## 依赖

- fastapi==0.115.0
- uvicorn==0.30.6
- httpx==0.27.2
- sqlalchemy[asyncio]>=2.0
- asyncpg>=0.29.0
- prometheus-client>=0.20.0

## 变更日志

| 日期 | 变更 |
|------|------|
| 2026-04-23 | 移除 NextStepSuggester（3x LLM 调用降为 2x）。添加已知问题与优化待办。标注中文唯一语言策略。移除 next_suggestions 协议说明。 |
| 2026-04-24 | 全量中文交互策略：所有 Worker/Supervisor 提示词改为中文，移除 NextStepSuggester 代码残留（类、枚举、suggester 实例化），前端 agents.js 去除下一步建议模式匹配。 |
