"""Background Celery task: problem quality auditor.

Fetches problems from the OJ Admin API, asks a local LLM (Ollama) to
evaluate completeness and compliance, and auto-fixes issues by writing
back corrected starter code / test cases / metadata.

Key design decisions:
- Uses a *separate* Ollama LLM (gemma4:31b) instead of the cloud LLM,
  because audit runs are long, batch-oriented, and must not consume
  chat-rate API quota.
- Avoids re-auditing already-processed problems via the problem_audit
  DB table (status != 'pending').
- Supports ``force=true`` to re-audit everything regardless of status.
- Each problem is audited as an individual Celery sub-task for
  fine-grained progress tracking and automatic retry on failure.
"""
import json
import logging
import time
import uuid
from datetime import datetime, timezone

import httpx
from celery import group

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger("ai-agent-lite.audit")

# ---------------------------------------------------------------------------
# OJ Admin API helpers (synchronous — Celery workers are sync by default)
# ---------------------------------------------------------------------------

def _oj_login() -> tuple[httpx.Client, str]:
    """Authenticate with the OJ Admin API and return (client, csrf_token)."""
    client = httpx.Client(base_url=settings.oj_api_url, timeout=30.0)
    # prime CSRF cookie
    r = client.get("/api/profile")
    r.raise_for_status()
    csrf = client.cookies.get("csrftoken", "")
    # login
    r = client.post(
        "/api/login",
        json={"username": settings.oj_admin_user, "password": settings.oj_admin_pass},
        headers={"X-CSRFToken": csrf},
    )
    r.raise_for_status()
    csrf = client.cookies.get("csrftoken", csrf)
    logger.info("OJ login succeeded, csrf=%s…", csrf[:8])
    return client, csrf


def _fetch_all_problems(client: httpx.Client, csrf: str) -> list[dict]:
    """Paginate through /api/admin/problem and return all problems."""
    problems = []
    page = 1
    while True:
        r = client.get(
            "/api/admin/problem",
            params={"limit": 100, "page": page},
            headers={"X-CSRFToken": csrf},
        )
        r.raise_for_status()
        data = r.json()
        if data.get("error") is not None:
            break
        results = data["data"]["results"]
        if not results:
            break
        problems.extend(results)
        page += 1
    logger.info("Fetched %d problems from OJ", len(problems))
    return problems


def _fetch_problem_detail(client: httpx.Client, csrf: str, db_id: int) -> dict | None:
    """Get full detail for a single problem."""
    r = client.get(
        "/api/admin/problem",
        params={"id": db_id},
        headers={"X-CSRFToken": csrf},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("error") is not None:
        logger.warning("Failed to fetch problem id=%d: %s", db_id, data.get("error"))
        return None
    return data.get("data") or data


def _update_problem(client: httpx.Client, csrf: str, payload: dict) -> bool:
    """PUT /api/admin/problem to update a problem. Returns True on success."""
    r = client.put(
        "/api/admin/problem",
        json=payload,
        headers={"X-CSRFToken": csrf},
    )
    if r.status_code >= 400:
        logger.error("Problem update failed id=%s status=%d: %s",
                     payload.get("_id"), r.status_code, r.text[:300])
        return False
    return True


# ---------------------------------------------------------------------------
# Ollama LLM call (synchronous, used in Celery worker)
# ---------------------------------------------------------------------------

def _call_ollama(prompt: str) -> str:
    """Send a completion request to the local Ollama instance.

    Uses the non-streaming endpoint for simplicity in background tasks.
    """
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_predict": 4096,
        },
    }
    timeout = settings.ollama_timeout
    with httpx.Client(timeout=timeout) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", "")
        return content.strip()


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

def _build_audit_prompt(problem: dict) -> str:
    """Build the LLM audit prompt for a single problem."""
    from app.prompts import get_prompt
    template = get_prompt("problem_auditor")
    if not template:
        # Fallback inline prompt
        template = _FALLBACK_PROMPT

    # Serialize the problem data for the LLM to inspect
    problem_data = json.dumps(problem, ensure_ascii=False, indent=2)

    return template.replace("{{PROBLEM_DATA}}", problem_data)


_FALLBACK_PROMPT = """You are an expert competitive programming problem quality auditor.

You will be given a JSON object representing a problem from an Online Judge system.
Your job is to evaluate the problem against these criteria and respond in **valid JSON only**:

1. **completeness**: Does the problem have a clear title, description, input description, output description, and at least 1 sample?
2. **test_cases**: Does the problem have valid test cases? (test_case_id non-empty)
3. **starter_code**: Does the problem have meaningful starter code templates for C, C++, Java, and Python3?
   Templates must include a solve() function signature and a main() that calls it.
4. **judge_compatibility**: Will the starter code compile and run on the judge?
   - C/C++ must have `#include` headers and `int main()`
   - Java must have `public class Main` with `public static void main`
   - Python3 must have `def solve()` and `if __name__ == '__main__'`
5. **metadata**: Does the problem have proper difficulty, source, tags, and time/memory limits?

Respond with a JSON object:
```json
{
  "status": "pass|fail",
  "issues": ["list of specific issues found"],
  "fixes": {
    "template": {"C": "...", "C++": "...", "Java": "...", "Python3": "..."},
    "title": "corrected title if needed, else null",
    "input_description": "corrected input desc if needed, else null",
    "output_description": "corrected output desc if needed, else null",
    "samples": [{"input": "...", "output": "..."}],
    "difficulty": "Low|Mid|High",
    "source": "source if needed",
    "tags": ["tag1", "tag2"]
  }
}
```

If status is "pass", fixes can all be null.
If status is "fail", provide corrected values in fixes for every issue you found.

Problem data:
{{PROBLEM_DATA}}
"""


# ---------------------------------------------------------------------------
# Database helpers (sync — Celery worker uses sync SQLAlchemy)
# ---------------------------------------------------------------------------

def _get_audit_record(problem_display_id: str) -> dict | None:
    """Check if a problem has already been audited in the audit table.

    Uses raw SQL via asyncpg imported synchronously as a stopgap.
    The Celery worker cannot use async SQLAlchemy directly.
    """
    import psycopg2
    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, issues, fixes, created_at, updated_at "
                "FROM {schema}.problem_audit WHERE problem_display_id = %s "
                "ORDER BY updated_at DESC LIMIT 1".format(schema=settings.db_schema),
                (problem_display_id,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "status": row[0],
                    "issues": row[1],
                    "fixes": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "updated_at": row[4].isoformat() if row[4] else None,
                }
            return None
    finally:
        conn.close()


def _upsert_audit_record(
    problem_display_id: str,
    problem_db_id: int,
    audit_status: str,
    issues: list,
    fixes: dict,
    llm_raw_response: str,
) -> None:
    """Insert or update an audit record."""
    import psycopg2
    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            # Check if record exists
            cur.execute(
                "SELECT id FROM {schema}.problem_audit WHERE problem_display_id = %s "
                "ORDER BY created_at DESC LIMIT 1".format(schema=settings.db_schema),
                (problem_display_id,),
            )
            existing = cur.fetchone()

            now = datetime.now(timezone.utc)
            issues_json = json.dumps(issues, ensure_ascii=False)
            fixes_json = json.dumps(fixes, ensure_ascii=False)

            if existing:
                cur.execute(
                    "UPDATE {schema}.problem_audit SET "
                    "status=%s, issues=%s, fixes=%s, llm_raw_response=%s, "
                    "updated_at=%s WHERE id=%s".format(schema=settings.db_schema),
                    (audit_status, issues_json, fixes_json, llm_raw_response, now, existing[0]),
                )
            else:
                cur.execute(
                    "INSERT INTO {schema}.problem_audit "
                    "(problem_display_id, problem_db_id, status, issues, fixes, "
                    "llm_raw_response, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)".format(
                        schema=settings.db_schema
                    ),
                    (problem_display_id, problem_db_id, audit_status,
                     issues_json, fixes_json, llm_raw_response, now, now),
                )
            conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Starter code templates (defaults when missing)
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATES = {
    "C": (
        '#include <stdio.h>\n'
        '#include <stdlib.h>\n'
        '\n'
        'void solve(void) {\n'
        '    int n;\n'
        '    scanf("%d", &n);\n'
        '    printf("%d\\n", n);\n'
        '}\n'
        '\n'
        'int main(void) {\n'
        '    solve();\n'
        '    return 0;\n'
        '}\n'
    ),
    "C++": (
        '#include <bits/stdc++.h>\n'
        'using namespace std;\n'
        '\n'
        'void solve() {\n'
        '    int n;\n'
        '    cin >> n;\n'
        '    cout << n << endl;\n'
        '}\n'
        '\n'
        'int main() {\n'
        '    ios::sync_with_stdio(false);\n'
        '    cin.tie(nullptr);\n'
        '    solve();\n'
        '    return 0;\n'
        '}\n'
    ),
    "Java": (
        'import java.util.*;\n'
        '\n'
        'public class Main {\n'
        '    static void solve(Scanner sc) {\n'
        '        int n = sc.nextInt();\n'
        '        System.out.println(n);\n'
        '    }\n'
        '\n'
        '    public static void main(String[] args) {\n'
        '        Scanner sc = new Scanner(System.in);\n'
        '        solve(sc);\n'
        '    }\n'
        '}\n'
    ),
    "Python3": (
        'def solve() -> None:\n'
        '    n = int(input())\n'
        '    print(n)\n'
        '\n'
        "if __name__ == '__main__':\n"
        '    solve()\n'
    ),
}


# ---------------------------------------------------------------------------
# Core audit task
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_single_problem",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="audit",
)
def audit_single_problem(self, problem_summary: dict) -> dict:
    """Audit a single problem via LLM and auto-fix if needed.

    Args:
        problem_summary: dict with at least _id, id, title.
    Returns:
        dict with audit result.
    """
    display_id = problem_summary["_id"]
    db_id = problem_summary["id"]
    title = problem_summary.get("title", display_id)

    logger.info("Auditing problem _id=%s (db_id=%d, title=%s)", display_id, db_id, title)

    # Step 1: Login to OJ and fetch full problem detail
    try:
        client, csrf = _oj_login()
        problem = _fetch_problem_detail(client, csrf, db_id)
        if problem is None:
            return {"_id": display_id, "status": "error", "message": "Failed to fetch problem detail"}
    except Exception as exc:
        logger.exception("OJ login/fetch failed for _id=%s", display_id)
        raise self.retry(exc=exc)
    finally:
        client.close()

    # Step 2: Ask LLM to audit
    prompt = _build_audit_prompt(problem)
    try:
        raw_response = _call_ollama(prompt)
    except Exception as exc:
        logger.exception("Ollama call failed for _id=%s", display_id)
        raise self.retry(exc=exc)

    # Step 3: Parse LLM response
    audit_result = _parse_llm_response(raw_response)

    # Step 4: Save audit record
    try:
        _upsert_audit_record(
            problem_display_id=display_id,
            problem_db_id=db_id,
            audit_status=audit_result["status"],
            issues=audit_result.get("issues", []),
            fixes=audit_result.get("fixes", {}),
            llm_raw_response=raw_response,
        )
    except Exception as exc:
        logger.exception("DB save failed for _id=%s", display_id)
        # Don't retry — audit is done, just DB write failed

    # Step 5: Auto-fix if status is "fail"
    if audit_result["status"] == "fail" and audit_result.get("fixes"):
        try:
            _apply_fixes(client, csrf, problem, audit_result["fixes"])
            logger.info("Auto-fixed problem _id=%s", display_id)
        except Exception:
            logger.exception("Auto-fix failed for _id=%s", display_id)
            # Record that fix attempt failed
            try:
                _upsert_audit_record(
                    problem_display_id=display_id,
                    problem_db_id=db_id,
                    audit_status="fix_failed",
                    issues=audit_result.get("issues", []),
                    fixes=audit_result.get("fixes", {}),
                    llm_raw_response=raw_response,
                )
            except Exception:
                pass

    return {
        "_id": display_id,
        "status": audit_result["status"],
        "issues": audit_result.get("issues", []),
    }


def _parse_llm_response(raw: str) -> dict:
    """Extract JSON from the LLM response, with fallback heuristics."""
    # Try to find a JSON block in the response
    json_start = raw.find("{")
    json_end = raw.rfind("}") + 1
    if json_start >= 0 and json_end > json_start:
        try:
            result = json.loads(raw[json_start:json_end])
            # Validate required fields
            if "status" in result:
                return result
        except json.JSONDecodeError:
            pass

    # Fallback: if no valid JSON, treat as error
    logger.warning("Could not parse LLM response as JSON, treating as error")
    return {
        "status": "error",
        "issues": ["LLM response was not valid JSON"],
        "fixes": {},
    }


def _apply_fixes(client: httpx.Client, csrf: str, problem: dict, fixes: dict) -> None:
    """Apply LLM-suggested fixes to a problem via the OJ Admin API."""
    updated = dict(problem)  # shallow copy

    # Apply template fixes
    if fixes.get("template"):
        merged_template = dict(updated.get("template") or {})
        for lang, code in fixes["template"].items():
            if code and isinstance(code, str):
                merged_template[lang] = code
        updated["template"] = merged_template

    # Apply text field fixes
    for field in ("title", "input_description", "output_description"):
        if fixes.get(field):
            updated[field] = fixes[field]

    # Apply samples fix
    if fixes.get("samples"):
        updated["samples"] = fixes["samples"]

    # Apply metadata fixes
    if fixes.get("difficulty"):
        updated["difficulty"] = fixes["difficulty"]
    if fixes.get("source"):
        updated["source"] = fixes["source"]
    if fixes.get("tags"):
        updated["tags"] = fixes["tags"]

    # Ensure required fields are still present
    for required in ("_id", "id", "test_case_id", "io_mode", "languages",
                     "rule_type", "spj", "visible"):
        if required not in updated and required in problem:
            updated[required] = problem[required]

    success = _update_problem(client, csrf, updated)
    if not success:
        raise RuntimeError(f"Problem update API returned error for _id={updated.get('_id')}")


# ---------------------------------------------------------------------------
# Batch audit task — orchestrator
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_all_problems",
    bind=True,
    queue="audit",
)
def audit_all_problems(self, force: bool = False) -> dict:
    """Orchestrate batch audit of all (or all un-audited) problems.

    Args:
        force: If True, re-audit all problems regardless of existing records.

    Returns:
        dict with batch_id, total count, and per-problem results.
    """
    batch_id = str(uuid.uuid4())[:8]
    logger.info("Batch audit %s started (force=%s)", batch_id, force)

    # Step 1: Login and fetch problem list
    try:
        client, csrf = _oj_login()
        problems = _fetch_all_problems(client, csrf)
    except Exception as exc:
        logger.exception("OJ login/fetch failed for batch audit %s", batch_id)
        raise self.retry(exc=exc)
    finally:
        client.close()

    # Step 2: Filter out already-audited problems (unless force)
    if not force:
        un_audited = []
        for p in problems:
            existing = _get_audit_record(p["_id"])
            if existing is None or existing["status"] in ("error", "fix_failed"):
                un_audited.append(p)
        target_problems = un_audited
        logger.info("Batch %s: %d of %d problems need auditing",
                     batch_id, len(target_problems), len(problems))
    else:
        target_problems = problems
        logger.info("Batch %s (force): re-auditing all %d problems",
                     batch_id, len(target_problems))

    if not target_problems:
        return {
            "batch_id": batch_id,
            "total": len(problems),
            "audited": 0,
            "skipped": len(problems),
            "message": "All problems already audited",
        }

    # Step 3: Dispatch individual audit tasks in a chord
    summaries = [
        {"_id": p["_id"], "id": p["id"], "title": p.get("title", "")}
        for p in target_problems
    ]

    # Run tasks sequentially within the batch to avoid overloading Ollama
    results = []
    for summary in summaries:
        try:
            result = audit_single_problem.apply_async(args=(summary,), queue="audit")
            # Wait for each task (with timeout)
            task_result = result.get(timeout=settings.ollama_timeout + 60)
            results.append(task_result)
        except Exception as exc:
            logger.exception("Audit task failed for _id=%s", summary["_id"])
            results.append({"_id": summary["_id"], "status": "error", "message": str(exc)})

    passed = sum(1 for r in results if r.get("status") == "pass")
    failed = sum(1 for r in results if r.get("status") == "fail")
    errors = sum(1 for r in results if r.get("status") in ("error", "fix_failed"))

    logger.info("Batch %s complete: %d passed, %d failed, %d errors",
                batch_id, passed, failed, errors)

    return {
        "batch_id": batch_id,
        "total": len(problems),
        "audited": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "results": results,
    }