---
name: prompts
description: "Skill for the Prompts area of cdut_stu_agents. 3 symbols across 1 files."
---

# Prompts

3 symbols | 1 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how get_prompt, render_prompt work
- Modifying prompts-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/app/prompts/__init__.py` | _load_prompt, get_prompt, render_prompt |

## Entry Points

Start here when exploring this area:

- **`get_prompt`** (Function) — `ai-agent-lite/app/prompts/__init__.py:28`
- **`render_prompt`** (Function) — `ai-agent-lite/app/prompts/__init__.py:42`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `get_prompt` | Function | `ai-agent-lite/app/prompts/__init__.py` | 28 |
| `render_prompt` | Function | `ai-agent-lite/app/prompts/__init__.py` | 42 |
| `_load_prompt` | Function | `ai-agent-lite/app/prompts/__init__.py` | 16 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Render_prompt → _load_prompt` | intra_community | 3 |

## How to Explore

1. `gitnexus_context({name: "get_prompt"})` — see callers and callees
2. `gitnexus_query({query: "prompts"})` — find related execution flows
3. Read key files listed above for implementation details
