---
name: routers
description: "Skill for the Routers area of cdut_stu_agents. 7 symbols across 2 files."
---

# Routers

7 symbols | 2 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how get_test_case_content, ws_handler work
- Modifying routers-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/routers/oj_test_cases.py` | _get_db_connection, _lookup_problem_by_display_id, _lookup_problem_by_numeric_id, _fetch_submission_detail_db, get_test_case_content |
| `ai-agent-lite/app/routers/websocket.py` | _parse_ws_message, ws_handler |

## Entry Points

Start here when exploring this area:

- **`get_test_case_content`** (Function) — `ai-agent-lite/app/routers/oj_test_cases.py:124`
- **`ws_handler`** (Function) — `ai-agent-lite/app/routers/websocket.py:59`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `get_test_case_content` | Function | `ai-agent-lite/app/routers/oj_test_cases.py` | 124 |
| `ws_handler` | Function | `ai-agent-lite/app/routers/websocket.py` | 59 |
| `_get_db_connection` | Function | `ai-agent-lite/app/routers/oj_test_cases.py` | 25 |
| `_lookup_problem_by_display_id` | Function | `ai-agent-lite/app/routers/oj_test_cases.py` | 32 |
| `_lookup_problem_by_numeric_id` | Function | `ai-agent-lite/app/routers/oj_test_cases.py` | 52 |
| `_fetch_submission_detail_db` | Function | `ai-agent-lite/app/routers/oj_test_cases.py` | 72 |
| `_parse_ws_message` | Function | `ai-agent-lite/app/routers/websocket.py` | 31 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Get_test_case_content → _get_db_connection` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "get_test_case_content"})` — see callers and callees
2. `gitnexus_query({query: "routers"})` — find related execution flows
3. Read key files listed above for implementation details
