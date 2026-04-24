# AI Agent 提示链详细说明

> 本文档描述 `ai-agent-lite` 系统中 AI Agent 的完整对话处理流程、提示词设计、路由逻辑及状态管理。

---

## 1. 系统架构概览

```
用户消息 (WebSocket)
        │
        ▼
┌─────────────────────────────────────────────┐
│            Supervisor (监督者)               │
│  ┌─────────────────────────────────────────┐ │
│  │ 1. 意图分类 (LLM Call #1)              │ │
│  │    classify_intent()                    │ │
│  └───────────────┬─────────────────────────┘ │
│                  │                           │
│  ┌───────────────▼─────────────────────────┐ │
│  │ 2. 情绪覆盖 / 效率覆盖                   │ │
│  │    _determine_agent()                    │ │
│  └───────────────┬─────────────────────────┘ │
│                  │                           │
│  ┌───────────────▼─────────────────────────┐ │
│  │ 3. Worker 处理 (LLM Call #2)            │ │
│  │    selected_worker.process()             │ │
│  └───────────────┬─────────────────────────┘ │
│                  │                           │
│  ┌───────────────▼─────────────────────────┐ │
│  │ 4. 下一步建议 (LLM Call #3)              │ │
│  │    NextStepSuggester.suggest()           │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**每次用户消息 = 3 次 LLM 调用**（意图分类 + Worker 响应 + 建议生成）

---

## 2. Agent 类型定义

| 类型 ID | 显示名称 | 图标 | 颜色 | 职责 |
|---------|----------|------|------|------|
| `code_reviewer` | 代码审查专家 | 💻 | #5a9fd4 | 代码质量、效率与风格评估 |
| `problem_analyzer` | 问题解析专家 | 🧠 | #9f5ad4 | 算法解释与问题拆解 |
| `contest_coach` | 竞赛教练 | 🏆 | #d45a5a | 竞赛策略与表现优化 |
| `learning_partner` | 学习伙伴 | 🤝 | #5ad47a | 情感支持与学习动力 |
| `learning_manager` | 学习管理专家 | 📊 | #d4a05a | 学习路径规划与进度管理 |
| `next_step_suggester` | 下一步建议 | — | — | 对话末尾生成后续行动建议 |

---

## 3. 提示链完整流程

### 3.1 连接初始化（每条 WebSocket 连接触发一次）

1. 创建新的 `Supervisor` 实例
2. 创建 5 个 Worker 实例（各持有 `llm_client`）
3. 创建 `NextStepSuggester` 实例
4. 从 PostgreSQL 加载或创建 Session
5. 从 `StateManager` 加载学生状态

### 3.2 消息处理（每条用户消息触发）

```
步骤 1  客户端发送: {"type": "query", "content": {"query": "..."}}
步骤 2  加载最近20条消息作为上下文
步骤 3  发送 trace: "意图识别"
步骤 4  supervisor.route_request() → LLM Call #1（意图分类）
步骤 5  发送 trace: "意图识别完成" + intent
步骤 6  _determine_agent() 根据意图 + 情绪/效率 → 选择 Worker
步骤 7  发送 trace: "{Agent显示名} 处理中"
步骤 8  selected_worker.process() → LLM Call #2（Worker响应）
步骤 9  发送 agent_info 事件（Agent元数据）
步骤 10 逐片发送 raw 事件（最大80字符/片）
步骤 11  supervisor.get_next_actions() → LLM Call #3（建议生成）
步骤 12  发送 next_suggestions 事件（如有建议）
步骤 13  发送 trace: "建议生成完成"
步骤 14  持久化 Assistant 消息到 DB
步骤 15  更新 StateManager 状态
步骤 16  发送 finish 事件
```

---

## 4. 提示词详解

### 4.1 意图分类提示词（Supervisor → LLM Call #1）

```
Classify the student's intent from programming competition training:

Input: "{user_input}"

Possible intents:
- code_review: Request for code analysis, optimization, or style feedback
- problem_help: Need help understanding or solving a problem
- contest_prep: Seeking competition strategies or pressure simulation
- emotional_support: Expressing frustration, confusion, or need for motivation
- learning_plan: Request for study recommendations or progress tracking
- general_question: Other algorithm/data structure questions

Return ONLY the intent name.
```

**特点**: 无 system prompt、无多轮上下文、单条 user message、仅返回意图名

**意图 → Agent 映射表**:

| 意图 | Agent |
|------|-------|
| `code_review` | CodeReviewerAgent |
| `problem_help` | ProblemAnalyzerAgent |
| `contest_prep` | ContestCoachAgent |
| `emotional_support` | LearningPartnerAgent |
| `learning_plan` | LearningManagerAgent |
| `general_question` | ProblemAnalyzerAgent |
| 未知/回退 | ProblemAnalyzerAgent |

### 4.2 情绪覆盖与效率覆盖

情绪和效率覆盖在意图映射**之前**执行，优先级更高：

| 条件 | 覆盖 Agent | 说明 |
|------|-----------|------|
| `frustration > 0.6` | LearningPartnerAgent | 挫败感强时优先情感支持 |
| `confusion > 0.7` | LearningPartnerAgent | 迷惑感强时优先情感支持 |
| `efficiency_trend < 0.7` | LearningManagerAgent | 效率低迷时优先学习规划 |

**情绪检测方式**: 关键词扫描最近3条消息

| 情绪维度 | 关键词 | 计分方式 |
|---------|--------|---------|
| frustration | "难""不会""崩溃""frustrat""hard""can't" | 出现次数 × 0.3，上限1.0 |
| excitement | "太好""明白了""excit""great""understand" | 同上 |
| confusion | "为什么""不懂""confus""why""don't understand" | 同上 |

### 4.3 CodeReviewerAgent 提示词

```
As an expert code reviewer for programming competitions, analyze this {language} code:

Code:
```{language}
{code}
```

Student's question: {user_input}

Provide structured analysis covering:
1. Logic Correctness (checkmark/warning/cross + brief explanation)
2. Time Complexity Analysis (Big O notation)
3. Space Complexity Analysis
4. Code Style Assessment (naming, structure, readability)
5. 3 Specific Improvement Suggestions

Format response clearly with sections.
IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
```

**输入**: `submitted_code`（来自学生状态）、`language`（默认"unknown"）、`user_input`
**元数据输出**: `{"analysis_type": "code_review", "language": language}`
**错误回退**: "代码分析暂时不可用。"

### 4.4 ProblemAnalyzerAgent 提示词

```
As a programming competition problem expert, help with problem analysis:

Problem Context: {problem_id}
Student's Question: {user_input}

Provide comprehensive guidance covering:
1. Problem Understanding (what is being asked)
2. Solution Approach (step-by-step strategy)
3. Algorithm Selection (optimal choices and alternatives)
4. Edge Cases to consider
5. Implementation Tips

Focus on teaching problem-solving thinking, not just giving answers.
IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
```

**输入**: `current_problem_id`（默认"unknown"）、`user_input`
**元数据输出**: `{"problem_id": problem_id, "analysis_depth": "detailed"}`
**错误回退**: "问题分析暂时不可用。"

### 4.5 ContestCoachAgent 提示词

```
As a programming competition coach, provide strategic advice:

Student's Situation: {user_input}

Focus on competition-specific guidance:
1. Time Management Strategies
2. Problem Selection Priority (easy/medium/hard)
3. Debugging under Pressure
4. Common Competition Pitfalls to Avoid
5. Mental Preparation Techniques

Use competitive but supportive tone.
IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
```

**输入**: 仅 `user_input`（无特定状态注入）
**元数据输出**: `{"coaching_type": "contest_strategy"}`
**错误回退**: "比赛指导暂时不可用。"

### 4.6 LearningPartnerAgent 提示词

```
As a supportive learning partner, provide emotional support:

Student's Expression: {user_input}
Detected Emotional State: {emotional_state}

Provide:
1. Empathetic acknowledgement of feelings
2. Encouragement and motivation
3. Growth mindset perspective
4. Practical coping strategies
5. Positive reinforcement of progress

Be warm, understanding, and genuinely supportive.
IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
```

**输入**: `user_input`、`emotion_tags`（注入为 `emotional_state` 字符串）
**元数据输出**: `{"support_type": "emotional", "emotional_state": emotional_state}`
**错误回退**: "I'm here to support you. Let's continue learning together."

### 4.7 LearningManagerAgent 提示词

```
As a learning manager, create personalized learning plan:

Current Knowledge State: {knowledge_graph}
Learning Efficiency: {efficiency}
Student's Request: {user_input}

Provide structured learning guidance:
1. Current Skill Assessment
2. Recommended Learning Objectives
3. Adaptive Difficulty Adjustment
4. Practice Problem Recommendations
5. Study Schedule Suggestions

Base recommendations on actual competency levels.
IMPORTANT: You must respond in Chinese (简体中文) only. All content must be in Chinese.
```

**输入**: `knowledge_graph_position`、`efficiency_trend`、`user_input`
**元数据输出**: `{"plan_type": "adaptive_learning", "efficiency_factor": efficiency}`
**错误回退**: "学习规划暂时不可用。"

### 4.8 NextStepSuggester 提示词

```
You are an AI programming-competition coach. Based on the conversation below, suggest 2-3 concrete
next actions the student could take.

Student's last message: {user_input}
AI agent role: {agent_type}
AI response summary: {agent_response[:600]}
Current context: problem_id={state.get('current_problem_id', 'N/A')}

Return JSON ONLY — no markdown, no explanation. Format:
{"suggestions":[{"type":"practice|learn|review|debug|compete","title":"short action title
in Chinese (简体中文)","target":"specific target or problem id","reason":"why this helps,
in Chinese (简体中文)"}]}

Keep titles under 20 characters. Keep reasons under 40 characters. Title and reason MUST be
in Chinese (简体中文).
```

**输出**: JSON 格式建议列表，最多3项
**验证**: 剥离 markdown 代码围栏、解析 JSON、截断标题≤20字/目标≤60字/理由≤40字
**失败模式**: 返回空列表（永不抛异常）

---

## 5. LLM 客户端配置

| 配置项 | 值 | 来源 |
|--------|----|----|
| 提供商 | OpenAI 兼容 API | DeepSeek |
| Base URL | 环境变量 `LITE_LLM_BASE_URL` | docker-compose |
| API Key | 环境变量 `LITE_LLM_API_KEY` | docker-compose |
| 默认模型 | `deepseek-chat` | 可通过 `LITE_LLM_MODEL` 覆盖 |
| Temperature | 0.3 | 硬编码 |
| 超时 | 30s | 可通过 `LITE_LLM_TIMEOUT` 覆盖 |
| 重试策略 | 最多2次，指数退避（2s×2^attempt） | 触发条件: 429/超时/5xx |
| 流式传输 | 代码中 `stream()` 存在但未被使用 | 已知问题 OPT-002 |

**实际响应流**: Worker 调用 `complete()` 获取完整结果 → 逐80字符切片通过 WebSocket `raw` 事件推送给前端（非 LLM 级别流式传输）

---

## 6. 状态管理

### 学生状态结构 (`StudentState`)

```python
{
    "current_problem_id": str | None,          # 当前题目ID
    "submitted_code": str | None,              # 已提交的代码
    "knowledge_graph_position": dict,           # {topic: mastery_level} 知识图谱
    "emotion_tags": dict,                       # 情绪标签 (frustration/excitement/confusion)
    "efficiency_trend": float,                  # 效率趋势 (默认1.0)
    "session_start_time": datetime,             # 会话开始时间
    "last_activity_time": datetime              # 最后活动时间
}
```

### 效率追踪算法

```
new_trend = old_trend × 0.8 + efficiency × 0.2
其中 efficiency = expected_time / actual_time（基于题目难度等级）
```

---

## 7. 路由决策优先级

```
1. 情绪覆盖: frustration > 0.6 或 confusion > 0.7 → LearningPartnerAgent
2. 效率覆盖: efficiency_trend < 0.7 → LearningManagerAgent
3. 意图映射: code_review / problem_help / contest_prep / emotional_support / learning_plan / general_question
4. 默认回退: ProblemAnalyzerAgent
```

---

## 8. WebSocket 事件协议

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| `query` | 客户端→服务端 | 用户消息，格式 `{"type":"query","content":{"query":"..."}}` |
| `trace` | 服务端→客户端 | 处理阶段标记，含阶段名和状态 |
| `agent_info` | 服务端→客户端 | Agent 元数据（名称、描述、图标、颜色） |
| `raw` | 服务端→客户端 | 响应文本片段（最大80字符/片） |
| `next_suggestions` | 服务端→客户端 | 后续行动建议列表 |
| `finish` | 服务端→客户端 | 处理完成信号 |

---

## 9. 已知问题与优化方向

| ID | 问题 | 状态 |
|----|------|------|
| OPT-001 | 每次请求3次LLM调用（意图+Worker+建议） | 待优化 |
| OPT-002 | Worker 使用 `complete()` 而非 `stream()`，无真正流式传输 | 待优化 |
| OPT-003 | `_load_context()` 存在重复加载风险 | 待优化 |
| OPT-004 | 未实现 scope guard（tutor_policy.py） | 未实现 |
| OPT-005 | 未实现 boundary router（boundary_router.py） | 未实现 |
| OPT-006 | 无响应格式化器 | 未实现 |
| OPT-007 | Supervisor 每条WS连接创建（无共享状态） | 设计如此 |
| OPT-008 | 状态写入无并发保护 | 待优化 |
| OPT-009 | 情绪分析仅为关键词匹配 | 待优化 |
| OPT-010 | 无 Web 检索模块 | 未实现 |

---

## 10. 数据模型

### Session（会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | String | 用户标识 |
| problem_id | String | 关联题目ID |
| title | String | 会话标题 |
| status | String | 会话状态 |
| supervisor_state | JSONB | Supervisor 状态快照 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Message（消息）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInt | 主键 |
| session_id | UUID (FK) | 关联会话 |
| role | String | 消息角色 |
| content | Text | 消息内容 |
| msg_type | String | 消息类型 |
| created_at | DateTime | 创建时间 |

### AuditLog（审计日志）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | BigInt | 主键 |
| request_id | UUID | 请求ID |
| session_id | UUID (FK) | 关联会话 |
| user_id | String | 用户标识 |
| event_type | String | 事件类型 |
| detail | JSONB | 事件详情 |
| created_at | DateTime | 创建时间 |

---

*文档生成时间: 2026-04-24 | 基于 ai-agent-lite 当前 master 分支代码*