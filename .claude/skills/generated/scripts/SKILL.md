---
name: scripts
description: "Skill for the Scripts area of cdut_stu_agents. 9 symbols across 2 files."
---

# Scripts

9 symbols | 2 files | Cohesion: 100%

## When to Use

- Working with code in `ai-agent-lite/`
- Understanding how test_auto_send_success_and_idempotency, test_first_ac_signal, test_retry_dlq_endpoint work
- Modifying scripts-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | _assert, _post_json, _build_payload, test_auto_send_success_and_idempotency, test_first_ac_signal (+1) |
| `ai-agent-lite/scripts/test_audit_single.py` | check_template, main, _indent |

## Entry Points

Start here when exploring this area:

- **`test_auto_send_success_and_idempotency`** (Function) — `ai-agent-lite/scripts/test_submission_fallback_e2e.py:103`
- **`test_first_ac_signal`** (Function) — `ai-agent-lite/scripts/test_submission_fallback_e2e.py:142`
- **`test_retry_dlq_endpoint`** (Function) — `ai-agent-lite/scripts/test_submission_fallback_e2e.py:183`
- **`check_template`** (Function) — `ai-agent-lite/scripts/test_audit_single.py:25`
- **`main`** (Function) — `ai-agent-lite/scripts/test_audit_single.py:47`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `test_auto_send_success_and_idempotency` | Function | `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | 103 |
| `test_first_ac_signal` | Function | `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | 142 |
| `test_retry_dlq_endpoint` | Function | `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | 183 |
| `check_template` | Function | `ai-agent-lite/scripts/test_audit_single.py` | 25 |
| `main` | Function | `ai-agent-lite/scripts/test_audit_single.py` | 47 |
| `_assert` | Function | `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | 38 |
| `_post_json` | Function | `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | 43 |
| `_build_payload` | Function | `ai-agent-lite/scripts/test_submission_fallback_e2e.py` | 74 |
| `_indent` | Function | `ai-agent-lite/scripts/test_audit_single.py` | 153 |

## How to Explore

1. `gitnexus_context({name: "test_auto_send_success_and_idempotency"})` — see callers and callees
2. `gitnexus_query({query: "scripts"})` — find related execution flows
3. Read key files listed above for implementation details
