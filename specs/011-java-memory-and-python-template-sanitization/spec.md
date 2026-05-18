# Spec: Fix Java/Python Runtime Error in OJ Submission Pipeline

## Background
Recent submissions show frequent `RUNTIME_ERROR` for Java and Python in OJ UI.

Observed symptoms:
- Java submissions fail with JVM bootstrap errors like:
  - `Could not reserve enough space for 65536KB object heap`
  - `Could not reserve enough space for code cache`
- Python submissions fail with syntax errors when source starts with template markers:
  - `//PREPEND BEGIN`
  - `SyntaxError: invalid syntax`

## Root Cause
### Java
The sandbox enforces memory limit directly from problem config (`memory_limit_kb = memory_limit_mb * 1024`).
For many problems (for example 512MB), current Java runtime flags still require more reserved memory in isolate rlimit mode, causing JVM init failure before user code executes.

### Python
The submission code may contain QDUOJ template marker blocks (`//PREPEND ... //TEMPLATE ... //APPEND`) intended for template composition. The current judge path forwards raw code directly to Python execution, so marker lines become invalid Python syntax.

## Requirements
1. Java submissions must not fail at JVM startup due to too-low sandbox memory budget.
2. Python submissions containing marker blocks must be sanitized before execution.
3. Preserve behavior for C/C++ and already-valid Java/Python submissions.
4. Keep API response schema unchanged.
5. Verify end-to-end in Docker environment only.

## Design
### 1) Java runtime memory floor in judge layer
- File: `ai-agent-lite/app/services/judge_service.py`
- Add language-aware effective memory policy:
  - Base memory from problem config remains unchanged for non-Java.
  - For Java, use `effective_memory_limit_kb = max(problem_limit_kb, 1048576)`.
- Pass `effective_memory_limit_kb` to sandbox API.

Rationale:
- This avoids fragile JVM bootstrap failures in isolate rlimit mode.
- Keeps low-risk scope: no sandbox protocol change, no DB migration.

### 2) Sanitize template marker wrappers before judging
- File: `ai-agent-lite/app/services/judge_service.py`
- Add preprocessing function that detects marker-formatted source and extracts executable body per language.
- Marker grammar supported:
  - `//PREPEND BEGIN ... //PREPEND END`
  - `//TEMPLATE BEGIN ... //TEMPLATE END`
  - `//APPEND BEGIN ... //APPEND END`
- For Python execution code:
  - If marker format exists, rebuild as `prepend + template + append` joined by newlines.
  - Otherwise keep original source.
- For Java execution code:
  - Apply same reconstruction to remove wrapper markers before compile.

Rationale:
- Prevents syntax errors from wrapper markers while preserving intended scaffold composition.

## Compatibility and Risk
- Compatibility:
  - External API payload/response unchanged.
  - Existing valid plain-source submissions unaffected.
- Risks:
  - Over-aggressive marker parsing could modify unusual user code containing marker-like comments.
- Mitigation:
  - Only activate reconstruction when full begin/end marker pairs are detected.

## Validation Plan
1. Build and recreate relevant Docker services.
2. Submit Java sample via judge API with problem that previously failed at 512MB.
3. Submit Python sample containing marker blocks.
4. Acceptance criteria:
  - Java result is no longer immediate JVM-init `RE` under same problem.
  - Python marker-wrapped submission no longer fails at line-1 marker syntax.
  - No regression on plain Python/Java submissions.

## Non-goals
- No change to frontend submission contract.
- No sandbox container architecture change.
- No global retuning of all language limits beyond Java floor.
