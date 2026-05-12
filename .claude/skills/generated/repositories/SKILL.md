---
name: repositories
description: "Skill for the Repositories area of cdut_stu_agents. 6 symbols across 3 files."
---

# Repositories

6 symbols | 3 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how get_by_idempotency, create_event, list_messages work
- Modifying repositories-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/repositories/submission_event_repo.py` | get_by_idempotency, create_event |
| `ai-agent-lite/app/repositories/message_repo.py` | list_messages, list_messages_as_dicts |
| `ai-agent-lite/app/repositories/audit_repo.py` | _is_safe_key, log_event |

## Entry Points

Start here when exploring this area:

- **`get_by_idempotency`** (Function) — `ai-agent-lite/app/repositories/submission_event_repo.py:13`
- **`create_event`** (Function) — `ai-agent-lite/app/repositories/submission_event_repo.py:48`
- **`list_messages`** (Function) — `ai-agent-lite/app/repositories/message_repo.py:30`
- **`list_messages_as_dicts`** (Function) — `ai-agent-lite/app/repositories/message_repo.py:55`
- **`log_event`** (Function) — `ai-agent-lite/app/repositories/audit_repo.py:23`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `get_by_idempotency` | Function | `ai-agent-lite/app/repositories/submission_event_repo.py` | 13 |
| `create_event` | Function | `ai-agent-lite/app/repositories/submission_event_repo.py` | 48 |
| `list_messages` | Function | `ai-agent-lite/app/repositories/message_repo.py` | 30 |
| `list_messages_as_dicts` | Function | `ai-agent-lite/app/repositories/message_repo.py` | 55 |
| `log_event` | Function | `ai-agent-lite/app/repositories/audit_repo.py` | 23 |
| `_is_safe_key` | Function | `ai-agent-lite/app/repositories/audit_repo.py` | 19 |

## How to Explore

1. `gitnexus_context({name: "get_by_idempotency"})` — see callers and callees
2. `gitnexus_query({query: "repositories"})` — find related execution flows
3. Read key files listed above for implementation details
