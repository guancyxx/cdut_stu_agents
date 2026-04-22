# Feature Specification: AI Tutor Chat System

**Feature Branch**: `001-ai-tutor`
**Created**: 2025-12-02
**Updated**: 2026-04-22
**Status**: In Progress
**Implementation**: ai-agent-lite (FastAPI) + frontend-vue-ai-chat (Vue 3)
**Original input**: "Develop AI tutor chat system based on AI agent"

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Basic Q&A chat | Done | WebSocket streaming via ai-agent-lite |
| Code snippet input | Done | Code editor in chat UI |
| OJ problem integration | Done | Problem panel + auto-session creation |
| OJ code submission | Done | Submit from chat, result display |
| Per-session submit drafts | Done | Language/code/state preserved across switches |
| Persistent session storage | Not yet | Currently in-memory only |
| User identity binding | Not yet | Sessions use client-generated IDs |
| Code review structure | Not yet | LLM output is unstructured text |
| Learning progress tracking | Not yet | No analytics implemented |
| Error debugging assistance | Partial | LLM can help, but no structured debug flow |

## User Scenarios & Testing

### User Story 1 - Basic Q&A (Priority: P1)

Students ask algorithm/data-structure questions in natural language and get clear explanations.

**Acceptance Scenarios**:
1. Student asks "What is binary search?" -> System returns definition, principle, and use cases
2. Student asks "How to compute time complexity?" -> System provides method and examples
3. Student asks vague question "Why is my code slow?" -> System guides student to provide more info

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
1. Student requests "Explain Union-Find" -> System provides definition, operations, code
2. Follow-up "Why path compression?" -> System explains performance improvement
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
| FR-001 | Text-based chat with natural language | Done |
| FR-002 | Answer algorithm/DS questions | Done |
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

- **WebSocket protocol**: Client sends `{type:"raw", content, session_id}`, receives `{type:"raw/finish/error", content}`
- **Context**: Each session carries history list; long conversations need truncation strategy
- **LLM**: DeepSeek-V3 via OpenAI-compatible streaming API
- **OJ integration**: REST API proxy from frontend to QDUOJ backend
- **Session isolation**: Currently by client-generated session_id; user_id binding TODO