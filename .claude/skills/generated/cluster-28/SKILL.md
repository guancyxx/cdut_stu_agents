---
name: cluster-28
description: "Skill for the Cluster_28 area of cdut_stu_agents. 7 symbols across 1 files."
---

# Cluster_28

7 symbols | 1 files | Cohesion: 93%

## When to Use

- Working with code in `frontend-vue-ai-chat/`
- Understanding how sanitizeHtmlContent, walk, detectContentType work
- Modifying cluster_28-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `frontend-vue-ai-chat/src/utils/validators.js` | sanitizeHtmlContent, walk, detectContentType, renderMessageContent, markedParse (+2) |

## Entry Points

Start here when exploring this area:

- **`sanitizeHtmlContent`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:91`
- **`walk`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:98`
- **`detectContentType`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:141`
- **`renderMessageContent`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:157`
- **`markedParse`** (Function) — `frontend-vue-ai-chat/src/utils/validators.js:197`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `sanitizeHtmlContent` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 91 |
| `walk` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 98 |
| `detectContentType` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 141 |
| `renderMessageContent` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 157 |
| `markedParse` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 197 |
| `dompurifySanitize` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 209 |
| `escapeHtml` | Function | `frontend-vue-ai-chat/src/utils/validators.js` | 229 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `RenderMessageContent → SanitizeTextInput` | cross_community | 4 |
| `RenderMessageContent → Walk` | intra_community | 4 |
| `RenderMessageContent → EscapeHtml` | intra_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Composables | 1 calls |

## How to Explore

1. `gitnexus_context({name: "sanitizeHtmlContent"})` — see callers and callees
2. `gitnexus_query({query: "cluster_28"})` — find related execution flows
3. Read key files listed above for implementation details
