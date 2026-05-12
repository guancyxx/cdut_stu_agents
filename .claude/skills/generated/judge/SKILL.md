---
name: judge
description: "Skill for the Judge area of cdut_stu_agents. 17 symbols across 1 files."
---

# Judge

17 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `oj-backend-overrides/`
- Understanding how process_pending_task, compile_spj, judge work
- Modifying judge-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `oj-backend-overrides/judge/dispatcher.py` | process_pending_task, _request, compile_spj, _mark_system_error, _compute_statistic_info (+12) |

## Entry Points

Start here when exploring this area:

- **`process_pending_task`** (Function) — `oj-backend-overrides/judge/dispatcher.py:23`
- **`compile_spj`** (Function) — `oj-backend-overrides/judge/dispatcher.py:79`
- **`judge`** (Function) — `oj-backend-overrides/judge/dispatcher.py:130`
- **`update_problem_status_rejudge`** (Function) — `oj-backend-overrides/judge/dispatcher.py:213`
- **`update_problem_status`** (Function) — `oj-backend-overrides/judge/dispatcher.py:249`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `DispatcherBase` | Class | `oj-backend-overrides/judge/dispatcher.py` | 54 |
| `SPJCompiler` | Class | `oj-backend-overrides/judge/dispatcher.py` | 68 |
| `JudgeDispatcher` | Class | `oj-backend-overrides/judge/dispatcher.py` | 90 |
| `process_pending_task` | Function | `oj-backend-overrides/judge/dispatcher.py` | 23 |
| `compile_spj` | Function | `oj-backend-overrides/judge/dispatcher.py` | 79 |
| `judge` | Function | `oj-backend-overrides/judge/dispatcher.py` | 130 |
| `update_problem_status_rejudge` | Function | `oj-backend-overrides/judge/dispatcher.py` | 213 |
| `update_problem_status` | Function | `oj-backend-overrides/judge/dispatcher.py` | 249 |
| `update_contest_problem_status` | Function | `oj-backend-overrides/judge/dispatcher.py` | 299 |
| `update_contest_rank` | Function | `oj-backend-overrides/judge/dispatcher.py` | 338 |
| `get_rank` | Function | `oj-backend-overrides/judge/dispatcher.py` | 342 |
| `_request` | Function | `oj-backend-overrides/judge/dispatcher.py` | 58 |
| `_mark_system_error` | Function | `oj-backend-overrides/judge/dispatcher.py` | 103 |
| `_compute_statistic_info` | Function | `oj-backend-overrides/judge/dispatcher.py` | 109 |
| `__init__` | Function | `oj-backend-overrides/judge/dispatcher.py` | 55 |
| `__init__` | Function | `oj-backend-overrides/judge/dispatcher.py` | 69 |
| `__init__` | Function | `oj-backend-overrides/judge/dispatcher.py` | 91 |

## How to Explore

1. `gitnexus_context({name: "process_pending_task"})` — see callers and callees
2. `gitnexus_query({query: "judge"})` — find related execution flows
3. Read key files listed above for implementation details
