# Feature Specification: AI Tutor Chat System

**Feature Branch**: `001-ai-tutor`
**Created**: 2025-12-02
**Updated**: 2026-04-23
**Status**: In Progress
**Implementation**: ai-agent-lite (FastAPI) + frontend-vue-ai-chat (Vue 3)
**Original input**: "Develop AI tutor chat system based on AI agent"
**Language Policy**: Chinese (简体中文) is the sole UI and interaction language. All user-facing text, prompts, and responses must be in Chinese. Code comments remain English per project convention.

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Basic Q&A chat | Done | WebSocket streaming via ai-agent-lite |
| Code snippet input | Done | Code editor in chat UI |
| OJ problem integration | Done | Problem panel + auto-session creation |
| OJ code submission | Done | Submit from chat, result display |
| Per-session submit drafts | Done | Language/code/state preserved across switches |
| Persistent session storage | Not yet | DB tables exist, session restore logic incomplete |
| User identity binding | Not yet | Sessions use client-generated IDs |
| Code review structure | Not yet | LLM output is unstructured text |
| Learning progress tracking | Not yet | No analytics implemented |
| Error debugging assistance | Partial | LLM can help, but no structured debug flow |
| Scope guard (non-programming rejection) | Not yet | tutor_policy.py not implemented |
| Online retrieval | Not yet | web_retrieval.py not implemented |
| Structured output format | Not yet | response_formatter.py not implemented |
| Per-agent next-step suggestions | Removed | Was generating 3x LLM calls per request; see Optimization Backlog |

## User Scenarios & Testing

### User Story 1 - Basic Q&A (Priority: P1)

Students ask algorithm/data-structure questions in Chinese and get clear explanations in Chinese.

**Acceptance Scenarios**:
1. Student asks "什么是二分查找？" -> System returns definition, principle, and use cases in Chinese
2. Student asks "如何计算时间复杂度？" -> System provides method and examples in Chinese
3. Student asks vague question "为什么我的代码很慢？" -> System guides student to provide more info

**Implementation**: Working via ai-agent-lite + DeepSeek LLM

---

### User Story 2 - Code Review (Priority: P2)

Students submit code snippets. AI analyzes logic, performance, and style.

**Acceptance Scenarios**:
1. Student pastes code -> System analyzes structure, identifies errors or performance issues
2. Code has O(n^2) complexity -> System suggests O(n log n) alternative
3. Code works but style is poor -> System provides naming/structure suggestions

**Implementation**: LLM can handle this conversationally. Structured output format not yet implemented.

---

### User Story 3 - Algorithm Explanation (Priority: P3)

Students request algorithm/data-structure explanations with pseudocode or code examples.

**Acceptance Scenarios**:
1. Student requests "解释一下并查集" -> System provides definition, operations, code in Chinese
2. Follow-up "为什么要路径压缩？" -> System explains performance improvement
3. Student wants practice example -> System provides relevant problem and approach

**Implementation**: Working conversationally via LLM

---

### User Story 4 - Error Debugging (Priority: P3)

Students submit error messages. AI analyzes cause and suggests fixes.

**Acceptance Scenarios**:
1. Runtime error + code -> System identifies problem line and suggests fix
2. Vague error -> System guides step-by-step debugging
3. Logic error -> System compares expected vs actual behavior

**Implementation**: LLM handles this conversationally. No structured debug flow yet.

---

### User Story 5 - Learning Progress (Priority: P4)

System records student history and provides personalized recommendations.

**Acceptance Scenarios**:
1. View learning history -> Show discussed topics, code reviews, time spent
2. Identify weak areas -> Suggest targeted practice problems
3. Complete a topic -> Recommend next-level content

**Implementation**: Not yet started. Requires persistent storage and analytics.

---

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Text-based chat with natural language (Chinese) | Done |
| FR-002 | Answer algorithm/DS questions in Chinese | Done |
| FR-003 | Code snippet input with language detection | Done |
| FR-004 | Code analysis (logic, performance, style) | Partial (unstructured) |
| FR-005 | Conversation history persistence | Not yet (in-memory only) |
| FR-006 | < 5s initial response | Dependent on LLM latency |
| FR-007 | Parse and display common error messages | Partial |
| FR-008 | Algorithm/DS explanation with code examples | Done (via LLM) |
| FR-009 | Learning history tracking | Not yet |
| FR-010 | Multi-user concurrent access | Partial (no user isolation) |
| FR-011 | Input filtering (malicious/invalid) | Not yet |
| FR-012 | Auto context truncation on long conversations | Not yet |
| FR-013 | Clear/reset conversation | Done (new session) |
| FR-014 | User identity from OJ auth | Not yet |
| FR-015 | Persistent storage of all conversations | Not yet |
| FR-016 | Scope guard: reject non-programming queries | Not yet |
| FR-017 | Online retrieval for docs/version queries | Not yet |
| FR-018 | Structured response format (sections + sources) | Not yet |
| FR-019 | Streaming response (token-by-token display) | Not yet (stream API exists but workers use complete()) |

## Key Entities

- **Session**: id, user_id, problem_id, created_at, updated_at, status
- **Message**: id, session_id, role (user/assistant), content, type, timestamp
- **CodeSnippet**: code, language, problem_id (within message context)
- **LearningRecord**: user_id, knowledge_points, problem_ids, timestamps *(planned)*

## Success Criteria

| ID | Criterion | Current Status |
|----|-----------|----------------|
| SC-001 | < 5s initial response (95%) | Achievable with DeepSeek |
| SC-002 | 50 concurrent users | Not verified |
| SC-003 | 80% helpful answers | Not measured |
| SC-004 | Code review identifies 3+ issue types | Partial |
| SC-005 | 3 clicks to chat history | Done |
| SC-006 | 99% availability (24h) | Not measured |
| SC-007 | 20-round context without loss | Not verified (no compression) |
| SC-008 | 5 effective conversations/week/student | Not measured |
| SC-009 | < 30 min per learning cycle | Not measured |
| SC-010 | 90% invalid input rejection | Not implemented |

## Architecture Notes

- **WebSocket protocol**: Client sends `{type:"query", content:{query}, session_id}`, receives `{type:"raw/finish/error/agent_info"}`
- **Context**: Each session carries history list; long conversations need truncation strategy
- **LLM**: DeepSeek-V3 via OpenAI-compatible streaming API
- **OJ integration**: REST API proxy from frontend to QDUOJ backend
- **Session isolation**: Currently by client-generated session_id; user_id binding TODO
- **Language**: All user-facing text is Chinese; system prompt instructs LLM to respond in Chinese

## Optimization Backlog

Issues identified during architecture review (2026-04-23). Ordered by priority.

### P0 — Critical performance and correctness

| ID | Issue | Description | Impact |
|----|-------|-------------|--------|
| OPT-001 | 3x LLM calls per request | Supervisor intent classification + Worker response + NextStepSuggester = 3 sequential LLM calls per user message | 3x cost, 3x latency. NextStepSuggester has been removed; intent classification merge is pending |
| OPT-002 | Workers use complete() not stream() | LlmClient.stream() is implemented but no worker calls it. Users wait for full generation before seeing any output | Perceived latency is maximal; streaming would show first token in ~1s |
| OPT-003 | Duplicate _load_context() definition | main.py defines `_load_context()` at line 117 and again at line 123. Second silently shadows the first | If definitions diverge, wrong one runs; currently harmless but a latent bug |

### P1 — Missing guardrails and modules

| ID | Issue | Description | Impact |
|----|-------|-------------|--------|
| OPT-004 | No scope guard | tutor_policy.py not implemented. Any query (including non-programming) is forwarded to LLM | Wastes LLM tokens on off-topic queries; no OUT_OF_SCOPE error code defined |
| OPT-005 | No boundary router | boundary_router.py not implemented. Supervisor uses single-shot intent classification instead of structured routing with scope/retrieval/answer_mode | Routing is coarse; cannot auto-decide retrieval or answer guidance-vs-full-solution |
| OPT-006 | No response formatter | response_formatter.py not implemented. LLM output is raw unstructured text | Code review responses lack guaranteed sections; no Sources tail for retrieval results |

### P2 — Architecture and robustness

| ID | Issue | Description | Impact |
|----|-------|-------------|--------|
| OPT-007 | Supervisor re-instantiated per WS connection | main.py line 229 creates `Supervisor(llm)` inside ws_handler. Each connection gets a fresh instance, no state sharing | State is not shared across connections; memory is wasted |
| OPT-008 | State manager has no concurrency protection | state_manager.active_states is a plain dict without locking | Concurrent WS connections writing same session may lose updates |
| OPT-009 | Emotion analysis is keyword matching only | supervisor._analyze_emotional_state() counts hardcoded Chinese/English keywords in last 3 messages | Prone to false positives/negatives; no real sentiment model |
| OPT-010 | No web retrieval | web_retrieval.py not implemented. Agent cannot fetch docs, version diffs, or external references | Answers lack external grounding; queries about version differences or official docs are answered from training data only |

### P3 — Polish and monitoring

| ID | Issue | Description | Impact |
|----|-------|-------------|--------|
| OPT-011 | Frontend has redundant regex agent detection | agents.js extractAgentFromMessage() uses regex on content to guess agent type, but backend already sends `agent_info` events | Dead code; can misidentify agent when response content matches wrong pattern |
| OPT-012 | No LLM call duration tracking in metrics | llm_request_duration_seconds Histogram exists but is never observed | Cannot measure actual LLM latency in production |
| OPT-013 | No rate limiting per user | Any user can send unlimited requests | Vulnerable to abuse; no per-user quota |

## Change Log

| Date | Change |
|------|--------|
| 2026-04-23 | Removed per-agent next-step suggestions (NextStepSuggester). Was causing 3x LLM calls per request. Added OPT-001..OPT-013 optimization backlog. Added Chinese-only language policy. Added FR-016..FR-019. |
| 2026-04-22 | Added supervisor pattern implementation status |
| 2025-12-02 | Initial spec |
