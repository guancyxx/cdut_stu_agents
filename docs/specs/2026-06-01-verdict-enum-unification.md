# Spec: Verdict Enum Unification + sandbox.py Dead Code Fix

**Date:** 2026-06-01
**Status:** Approved (per ShuJieTai task board P1-SOLID)
**Author:** Hermes Agent

## Objective

Unify Verdict to a single source of truth, fix unreachable dead code in the
verdict-mapping logic, and remove a dataclass/Exception anti-pattern.

## Scope

### In Scope

- Add `Verdict(str, Enum)` to `ai-agent-lite/app/models/enums.py`
- Delete `class Verdict` (plain class) from `ai-agent-lite/app/services/judge_service.py`, import from enums
- Delete `class Verdict(str, Enum)` from `ai-agent-lite/app/services/sandbox.py`, import from enums
- Delete unreachable `if status == "SG": return Verdict.SE` block in `ai-agent-lite/app/services/sandbox.py:429-430`
- Remove `@dataclass` from `SandboxError(Exception)` in `ai-agent-lite/app/services/sandbox.py:109`, convert to plain class
- Mirror same fixes in root `sandbox/sandbox.py` (separate Docker image, needs its own local `sandbox/enums.py`)

### Out of Scope

- Merging ai-agent-lite sandbox.py with root sandbox/sandbox.py (they serve different containers)
- Runtime testing of the sandbox Docker container

## Technical Approach

1. ai-agent-lite: Verdict lives in `models/enums.py` (same module as AgentType, ErrorCode)
2. root sandbox: Verdict lives in `sandbox/enums.py` (standalone, identical definition)
3. Dead code: second `status == "SG"` branch is unreachable (first returns RE); remove lines 429-430
4. SandboxError: plain class with manual `__init__` instead of `@dataclass`

## Affected Files

- `ai-agent-lite/app/models/enums.py` — add Verdict
- `ai-agent-lite/app/models/__init__.py` — re-export Verdict
- `ai-agent-lite/app/services/judge_service.py` — remove Verdict class, import from enums
- `ai-agent-lite/app/services/sandbox.py` — remove Verdict, SandboxError fix, dead code fix
- `sandbox/enums.py` — new file
- `sandbox/sandbox.py` — mirror all fixes
- `sandbox/Dockerfile` — COPY enums.py

## Acceptance Criteria

- Verdict is defined once per codebase (models/enums.py for ai-agent-lite, sandbox/enums.py for sandbox container)
- All verdict values (AC/WA/TLE/MLE/RE/CE/SE) remain usable
- Dead code at sandbox.py:425-430 removed
- SandboxError is a plain Exception subclass, not a dataclass
- Python syntax check passes on all changed files
- Docker build succeeds for ai-agent-lite service
