---
name: models
description: "Skill for the Models area of cdut_stu_agents. 7 symbols across 1 files."
---

# Models

7 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how Base, Session, Message work
- Modifying models-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/models/orm.py` | Base, Session, Message, AuditLog, ProblemAudit (+2) |

## Entry Points

Start here when exploring this area:

- **`Base`** (Class) — `ai-agent-lite/app/models/orm.py:14`
- **`Session`** (Class) — `ai-agent-lite/app/models/orm.py:18`
- **`Message`** (Class) — `ai-agent-lite/app/models/orm.py:38`
- **`AuditLog`** (Class) — `ai-agent-lite/app/models/orm.py:55`
- **`ProblemAudit`** (Class) — `ai-agent-lite/app/models/orm.py:73`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Base` | Class | `ai-agent-lite/app/models/orm.py` | 14 |
| `Session` | Class | `ai-agent-lite/app/models/orm.py` | 18 |
| `Message` | Class | `ai-agent-lite/app/models/orm.py` | 38 |
| `AuditLog` | Class | `ai-agent-lite/app/models/orm.py` | 55 |
| `ProblemAudit` | Class | `ai-agent-lite/app/models/orm.py` | 73 |
| `SubmissionEvent` | Class | `ai-agent-lite/app/models/orm.py` | 108 |
| `SubmissionEventDLQ` | Class | `ai-agent-lite/app/models/orm.py` | 145 |

## How to Explore

1. `gitnexus_context({name: "Base"})` — see callers and callees
2. `gitnexus_query({query: "models"})` — find related execution flows
3. Read key files listed above for implementation details
