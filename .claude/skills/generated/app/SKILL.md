---
name: app
description: "Skill for the App area of cdut_stu_agents. 12 symbols across 3 files."
---

# App

12 symbols | 3 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how complete, stream, get_llm_client work
- Modifying app-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/llm_client.py` | _get_system_prompt, _inject_system, complete, stream, _fallback |
| `ai-agent-lite/app/di.py` | get_llm_client, get_supervisor, get_workers, get_suggester, get_emotion_analyzer |
| `ai-agent-lite/app/database.py` | _apply_schema, init_db |

## Entry Points

Start here when exploring this area:

- **`complete`** (Function) — `ai-agent-lite/app/llm_client.py:56`
- **`stream`** (Function) — `ai-agent-lite/app/llm_client.py:111`
- **`get_llm_client`** (Function) — `ai-agent-lite/app/di.py:23`
- **`get_supervisor`** (Function) — `ai-agent-lite/app/di.py:31`
- **`get_workers`** (Function) — `ai-agent-lite/app/di.py:39`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `complete` | Function | `ai-agent-lite/app/llm_client.py` | 56 |
| `stream` | Function | `ai-agent-lite/app/llm_client.py` | 111 |
| `get_llm_client` | Function | `ai-agent-lite/app/di.py` | 23 |
| `get_supervisor` | Function | `ai-agent-lite/app/di.py` | 31 |
| `get_workers` | Function | `ai-agent-lite/app/di.py` | 39 |
| `get_suggester` | Function | `ai-agent-lite/app/di.py` | 62 |
| `get_emotion_analyzer` | Function | `ai-agent-lite/app/di.py` | 70 |
| `init_db` | Function | `ai-agent-lite/app/database.py` | 24 |
| `_get_system_prompt` | Function | `ai-agent-lite/app/llm_client.py` | 43 |
| `_inject_system` | Function | `ai-agent-lite/app/llm_client.py` | 50 |
| `_fallback` | Function | `ai-agent-lite/app/llm_client.py` | 158 |
| `_apply_schema` | Function | `ai-agent-lite/app/database.py` | 19 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Complete → _get_system_prompt` | intra_community | 3 |
| `Stream → _get_system_prompt` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "complete"})` — see callers and callees
2. `gitnexus_query({query: "app"})` — find related execution flows
3. Read key files listed above for implementation details
