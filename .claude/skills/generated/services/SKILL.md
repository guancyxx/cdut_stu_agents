---
name: services
description: "Skill for the Services area of cdut_stu_agents. 30 symbols across 9 files."
---

# Services

30 symbols | 9 files | Cohesion: 89%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how requestJson, login, register work
- Modifying services-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend-vue-ai-chat/src/services/apiClient.js` | requestJson, login, register, logout, fetchProblems (+3) |
| `ai-agent-lite/app/services/supervisor.py` | route_request, _classify_intent, _update_state_from_context, _analyze_emotional_state_async, _determine_agent (+3) |
| `ai-agent-lite/app/services/submission_summary.py` | _safe_int, _clip_text, _redact_sensitive, build_submission_summary |
| `ai-agent-lite/app/services/state_manager.py` | load_state, save_state, track_efficiency |
| `ai-agent-lite/app/services/submission_recommendation.py` | _get_db_connection, recommend_next_problem |
| `ai-agent-lite/app/routers/submission_events.py` | _normalize_event_payload, ingest_submission_fallback |
| `ai-agent-lite/app/services/intent_classifier.py` | classify |
| `ai-agent-lite/app/services/knowledge_assessor.py` | assess |
| `ai-agent-lite/app/services/conversation_orchestrator.py` | process_turn |

## Entry Points

Start here when exploring this area:

- **`requestJson`** (Function) — `frontend-vue-ai-chat/src/services/apiClient.js:1`
- **`login`** (Function) — `frontend-vue-ai-chat/src/services/apiClient.js:37`
- **`register`** (Function) — `frontend-vue-ai-chat/src/services/apiClient.js:48`
- **`logout`** (Function) — `frontend-vue-ai-chat/src/services/apiClient.js:59`
- **`fetchProblems`** (Function) — `frontend-vue-ai-chat/src/services/apiClient.js:70`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `requestJson` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 1 |
| `login` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 37 |
| `register` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 48 |
| `logout` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 59 |
| `fetchProblems` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 70 |
| `submitCode` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 75 |
| `fetchSubmissions` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 87 |
| `fetchSubmissionDetail` | Function | `frontend-vue-ai-chat/src/services/apiClient.js` | 92 |
| `route_request` | Function | `ai-agent-lite/app/services/supervisor.py` | 27 |
| `classify` | Function | `ai-agent-lite/app/services/intent_classifier.py` | 28 |
| `build_submission_summary` | Function | `ai-agent-lite/app/services/submission_summary.py` | 45 |
| `recommend_next_problem` | Function | `ai-agent-lite/app/services/submission_recommendation.py` | 17 |
| `ingest_submission_fallback` | Function | `ai-agent-lite/app/routers/submission_events.py` | 121 |
| `load_state` | Function | `ai-agent-lite/app/services/state_manager.py` | 22 |
| `save_state` | Function | `ai-agent-lite/app/services/state_manager.py` | 38 |
| `track_efficiency` | Function | `ai-agent-lite/app/services/state_manager.py` | 67 |
| `assess` | Function | `ai-agent-lite/app/services/knowledge_assessor.py` | 27 |
| `process_turn` | Function | `ai-agent-lite/app/services/conversation_orchestrator.py` | 50 |
| `_classify_intent` | Function | `ai-agent-lite/app/services/supervisor.py` | 51 |
| `_update_state_from_context` | Function | `ai-agent-lite/app/services/supervisor.py` | 136 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `SubmitSolution → RequestJson` | cross_community | 4 |
| `Register → RequestJson` | cross_community | 4 |
| `Login → RequestJson` | cross_community | 4 |
| `HydrateAuthSession → RequestJson` | cross_community | 4 |
| `Ingest_submission_fallback → _get_db_connection` | intra_community | 3 |
| `Route_request → _analyze_emotional_state_async` | intra_community | 3 |
| `Route_request → Classify` | intra_community | 3 |
| `Route_request → _needs_emotional_support` | cross_community | 3 |
| `Route_request → _needs_difficulty_adjustment` | cross_community | 3 |
| `Route_request → _is_continuation_of_same_flow` | cross_community | 3 |

## How to Explore

1. `gitnexus_context({name: "requestJson"})` — see callers and callees
2. `gitnexus_query({query: "services"})` — find related execution flows
3. Read key files listed above for implementation details
