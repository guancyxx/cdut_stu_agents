---
name: tasks
description: "Skill for the Tasks area of cdut_stu_agents. 24 symbols across 2 files."
---

# Tasks

24 symbols | 2 files | Cohesion: 82%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how audit_next_problem, audit_all_problems, reset_audit_state work
- Modifying tasks-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/tasks/problem_auditor.py` | _update_problem, _call_xiaomi, _build_audit_prompt, _get_next_local_unaudited, _ensure_template_markers (+17) |
| `ai-agent-lite/app/tasks/submission_events.py` | retry_submission_dlq_task, _run |

## Entry Points

Start here when exploring this area:

- **`audit_next_problem`** (Function) — `ai-agent-lite/app/tasks/problem_auditor.py:818`
- **`audit_all_problems`** (Function) — `ai-agent-lite/app/tasks/problem_auditor.py:853`
- **`reset_audit_state`** (Function) — `ai-agent-lite/app/tasks/problem_auditor.py:904`
- **`audit_single_problem`** (Function) — `ai-agent-lite/app/tasks/problem_auditor.py:725`
- **`retry_submission_dlq_task`** (Function) — `ai-agent-lite/app/tasks/submission_events.py:22`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `audit_next_problem` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 818 |
| `audit_all_problems` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 853 |
| `reset_audit_state` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 904 |
| `audit_single_problem` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 725 |
| `retry_submission_dlq_task` | Function | `ai-agent-lite/app/tasks/submission_events.py` | 22 |
| `_update_problem` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 81 |
| `_call_xiaomi` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 100 |
| `_build_audit_prompt` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 242 |
| `_get_next_local_unaudited` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 278 |
| `_ensure_template_markers` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 538 |
| `_apply_fixes` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 653 |
| `_parse_llm_response` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 697 |
| `_do_audit_problem` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 749 |
| `_pg_connect` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 257 |
| `_get_all_audited_ids` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 264 |
| `_get_all_local_problems` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 318 |
| `_get_local_problem_count` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 331 |
| `_upsert_audit_record` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 346 |
| `_delete_audit_record` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 394 |
| `_clear_all_audit_records` | Function | `ai-agent-lite/app/tasks/problem_auditor.py` | 410 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Audit_single_problem → _oj_login` | cross_community | 3 |
| `Audit_single_problem → _fetch_problem_detail` | cross_community | 3 |
| `Audit_single_problem → _build_audit_prompt` | cross_community | 3 |
| `Audit_single_problem → _call_xiaomi` | cross_community | 3 |
| `Audit_next_problem → _pg_connect` | cross_community | 3 |
| `Audit_next_problem → _oj_login` | cross_community | 3 |
| `Audit_next_problem → _fetch_problem_detail` | cross_community | 3 |
| `Audit_next_problem → _build_audit_prompt` | intra_community | 3 |
| `Audit_next_problem → _call_xiaomi` | intra_community | 3 |
| `Audit_all_problems → _pg_connect` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "audit_next_problem"})` — see callers and callees
2. `gitnexus_query({query: "tasks"})` — find related execution flows
3. Read key files listed above for implementation details
