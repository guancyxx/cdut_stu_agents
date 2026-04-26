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
- The beat-scheduled ``audit_next_problem`` runs every 10 minutes and
  picks exactly ONE un-audited problem at a time, ensuring the local
  GPU is never overloaded with concurrent LLM inference requests.
"""
import json
import logging
import uuid
from datetime import datetime, timezone

import httpx

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


def _fetch_problem_list(client: httpx.Client, csrf: str, limit: int = 0) -> list[dict]:
    """Fetch problem summaries from the OJ Admin API.

    Args:
        limit: Maximum number of problems to fetch. 0 means all.
               For large OJ instances, use a reasonable limit (e.g. 50-200).
    """
    problems = []
    page = 1
    per_page = 100
    while True:
        r = client.get(
            "/api/admin/problem",
            params={"limit": per_page, "page": page},
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
        # Stop if we have enough
        if limit > 0 and len(problems) >= limit:
            problems = problems[:limit]
            break
        # Stop if this page was not full (no more pages)
        if len(results) < per_page:
            break
        page += 1

        # Safety: avoid runaway pagination on very large databases
        if limit == 0 and page > 5000:
            logger.warning("Pagination safety limit reached at page %d, stopping fetch", page)
            break

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
# Database helpers (sync — Celery worker uses psycopg2 directly)
# ---------------------------------------------------------------------------

def _get_all_audited_ids() -> set[str]:
    """Fetch all problem_display_ids that have a successful audit record.

    Returns a set of display IDs for fast membership checking.
    Only includes records with status 'pass' (skip on 'fail' so they get retried).
    """
    import psycopg2
    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT problem_display_id FROM {schema}.problem_audit "
                "WHERE status = 'pass'".format(schema=settings.db_schema)
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def _get_next_unaudited_problem() -> dict | None:
    """Fetch ONE un-audited problem from the OJ.

    Strategy:
    1. Get all already-audited display_ids from the DB.
    2. Fetch the latest page of problems from the OJ.
    3. Return the first problem whose _id is not in the audit table.
       If all on the first page are audited, fetch more pages.
    Returns None if all problems are audited.
    """
    import psycopg2

    # Step 1: get audited ids
    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    audited_ids: set[str] = set()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT problem_display_id FROM {schema}.problem_audit".format(
                    schema=settings.db_schema
                )
            )
            audited_ids = {row[0] for row in cur.fetchall()}
    finally:
        conn.close()

    # Step 2: paginate through OJ to find an un-audited problem
    try:
        client, csrf = _oj_login()
    except Exception:
        logger.exception("OJ login failed in _get_next_unaudited_problem")
        return None

    try:
        page = 1
        per_page = 100
        max_pages = 100  # safety: don't scan more than 100 pages
        while page <= max_pages:
            r = client.get(
                "/api/admin/problem",
                params={"limit": per_page, "page": page},
                headers={"X-CSRFToken": csrf},
            )
            r.raise_for_status()
            data = r.json()
            if data.get("error") is not None or not data.get("data", {}).get("results"):
                break

            results = data["data"]["results"]
            for p in results:
                if p["_id"] not in audited_ids:
                    logger.info("Found un-audited problem: _id=%s (page %d)", p["_id"], page)
                    return p

            if len(results) < per_page:
                break
            page += 1
    except Exception:
        logger.exception("OJ fetch failed in _get_next_unaudited_problem")
        return None
    finally:
        client.close()

    logger.info("All problems are audited (scanned %d pages)", page)
    return None


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
            existing = cur.execute(
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
# Quick pre-check: skip problems that are clearly fine without LLM
# ---------------------------------------------------------------------------

def _quick_check_problem(problem: dict) -> list[str]:
    """Fast heuristic check for obvious issues. Returns list of issue strings.

    Empty list means no obvious issues detected (still needs LLM audit).
    This is used to skip problems that are trivially incomplete.
    """
    issues = []

    # Check title
    if not problem.get("title") or not problem["title"].strip():
        issues.append("Missing or empty title")

    # Check description
    desc = problem.get("description") or ""
    if not desc.strip() or len(desc.strip()) < 10:
        issues.append("Description too short or empty")

    # Check samples
    samples = problem.get("samples") or []
    if not samples:
        issues.append("No sample input/output")

    # Check template (starter code)
    template = problem.get("template") or {}
    missing_langs = []
    for lang in ("C", "C++", "Java", "Python3"):
        code = template.get(lang, "") or ""
        if not code.strip():
            missing_langs.append(lang)
    if missing_langs:
        issues.append(f"Missing starter code for: {', '.join(missing_langs)}")

    # Check test_case_id
    tc_id = problem.get("test_case_id") or ""
    if not tc_id.strip():
        issues.append("Empty test_case_id")

    return issues


# ---------------------------------------------------------------------------
# Core audit task — audits exactly ONE problem per invocation
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_single_problem",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="audit",
    soft_time_limit=600,   # 10 min soft (matches the beat interval)
    time_limit=660,         # 11 min hard limit
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
    return _do_audit_problem(display_id, db_id, title, retry_on_failure=self)


def _do_audit_problem(
    display_id: str,
    db_id: int,
    title: str,
    retry_on_failure=None,
) -> dict:
    """Core audit logic: fetch problem detail -> LLM audit -> save -> auto-fix.

    Args:
        display_id: Problem display ID (e.g. "LQ1273").
        db_id: Problem database ID.
        title: Problem title.
        retry_on_failure: Optional Celery self reference for retry support.
            Pass None when called from non-Celery context (e.g. beat task).
    Returns:
        dict with audit result.
    """
    logger.info("Auditing problem _id=%s (db_id=%d, title=%s)", display_id, db_id, title)

    # Step 1: Login to OJ and fetch full problem detail
    client = None
    try:
        client, csrf = _oj_login()
        problem = _fetch_problem_detail(client, csrf, db_id)
        if problem is None:
            return {"_id": display_id, "status": "error", "message": "Failed to fetch problem detail"}
    except Exception as exc:
        logger.exception("OJ login/fetch failed for _id=%s", display_id)
        if retry_on_failure:
            raise retry_on_failure.retry(exc=exc)
        raise

    try:
        # Step 2: Ask LLM to audit
        prompt = _build_audit_prompt(problem)
        try:
            raw_response = _call_ollama(prompt)
        except Exception as exc:
            logger.exception("Ollama call failed for _id=%s", display_id)
            if retry_on_failure:
                raise retry_on_failure.retry(exc=exc)
            raise

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
        except Exception:
            logger.exception("DB save failed for _id=%s", display_id)

        # Step 5: Auto-fix if status is "fail"
        if audit_result["status"] == "fail" and audit_result.get("fixes"):
            try:
                _apply_fixes(client, csrf, problem, audit_result["fixes"])
                logger.info("Auto-fixed problem _id=%s", display_id)
            except Exception:
                logger.exception("Auto-fix failed for _id=%s", display_id)
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
    finally:
        if client:
            client.close()


# ---------------------------------------------------------------------------
# Beat-scheduled task: audit exactly ONE problem per tick (every 10 min)
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_next_problem",
    queue="audit",
    soft_time_limit=600,
    time_limit=660,
)
def audit_next_problem() -> dict:
    """Find and audit exactly ONE un-audited problem.

    This is the task triggered by Celery Beat every 10 minutes.
    It picks the next un-audited problem from OJ, runs the full
    audit+fix pipeline on it, and returns the result.

    The design ensures only one LLM inference runs at a time,
    keeping the local GPU fully available for interactive use.

    IMPORTANT: We run the audit logic directly (not via apply_async)
    because concurrency=1 means calling .get() on a sub-task would
    deadlock the sole worker.
    """
    problem = _get_next_unaudited_problem()
    if problem is None:
        logger.info("No un-audited problems found — all done")
        return {"status": "no_work", "message": "All problems audited"}

    display_id = problem["_id"]
    db_id = problem["id"]
    title = problem.get("title", display_id)
    logger.info("Beat tick: auditing problem _id=%s (db_id=%d, title=%s)",
                display_id, db_id, title)

    # Run the audit logic directly (no sub-task delegation)
    return _do_audit_problem(display_id, db_id, title)


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


def _ensure_template_markers(code: str, lang: str) -> str:
    """Ensure a template string uses the //PREPEND/TEMPLATE/APPEND marker format.

    If the code already contains the markers, return it unchanged.
    Otherwise, wrap the bare code into the correct marker structure for QDUOJ.

    QDUOJ's parse_problem_template() regex matches ONLY '//PREFIX BEGIN/END'
    markers (not '#'). Templates without markers are silently treated as empty,
    causing students to see a blank editor. This function prevents that.
    """
    if "//TEMPLATE BEGIN" in code:
        # Already has markers — trust it
        return code

    # Split bare code into prepend / template / append sections
    lines = code.split("\n")

    if lang == "Python3":
        # Python3: find def solve() -> template, if __name__ -> append
        # Also strip any 'import sys' from prepend (use input() instead)
        prepend_lines = []
        template_lines = []
        append_lines = []
        in_append = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("if __name__") or stripped == "if __name__ == '__main__':":
                in_append = True
                append_lines.append(line)
                continue
            if in_append:
                append_lines.append(line)
                continue
            # Skip 'import sys' lines — we prefer input() for beginners
            if stripped == "import sys" or stripped.startswith("import sys #"):
                continue
            # Def solve starts the template section
            if not template_lines and stripped.startswith("def solve"):
                template_lines.append(line)
                continue
            if template_lines:
                template_lines.append(line)
            else:
                prepend_lines.append(line)

        # Filter out empty-only prepend
        prepend_text = "\n".join(prepend_lines).strip()
        template_text = "\n".join(template_lines)
        append_text = "\n".join(append_lines)

        # Build marked template
        result = f"//PREPEND BEGIN\n{prepend_text}\n//PREPEND END\n\n"
        result += f"//TEMPLATE BEGIN\n{template_text}\n//TEMPLATE END\n\n"
        result += f"//APPEND BEGIN\n{append_text}\n//APPEND END"
        return result

    elif lang in ("C", "C++"):
        # C/C++: lines before void solve() -> prepend, void solve() -> template,
        # int main() -> append
        prepend_lines = []
        template_lines = []
        append_lines = []
        in_append = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("int main("):
                in_append = True
                append_lines.append(line)
                continue
            if in_append:
                append_lines.append(line)
                continue
            # Check if we're in the function body
            if not template_lines and (stripped.startswith("void solve") or stripped.startswith("int solve")):
                template_lines.append(line)
                continue
            if template_lines:
                template_lines.append(line)
            else:
                prepend_lines.append(line)

        prepend_text = "\n".join(prepend_lines)
        template_text = "\n".join(template_lines)
        append_text = "\n".join(append_lines)

        result = f"//PREPEND BEGIN\n{prepend_text}\n//PREPEND END\n\n"
        result += f"//TEMPLATE BEGIN\n{template_text}\n//TEMPLATE END\n\n"
        result += f"//APPEND BEGIN\n{append_text}\n//APPEND END"
        return result

    elif lang == "Java":
        # Java: find 'public static void solve' -> template,
        # 'public static void main' -> append, everything before -> prepend
        prepend_lines = []
        template_lines = []
        append_lines = []
        in_template = False
        in_append = False
        brace_depth = 0

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("public static void solve"):
                in_template = True
                brace_depth = 0
                template_lines.append(line)
                brace_depth += line.count("{") - line.count("}")
                continue
            if in_template and not in_append:
                template_lines.append(line)
                brace_depth += line.count("{") - line.count("}")
                if brace_depth <= 0 and "{" in "".join(template_lines):
                    in_template = False
                continue
            if stripped.startswith("public static void main"):
                in_append = True
            if in_append:
                append_lines.append(line)
                continue
            prepend_lines.append(line)

        # If prepend ends with class opening, ensure it's there
        prepend_text = "\n".join(prepend_lines)
        template_text = "\n".join(template_lines)
        append_text = "\n".join(append_lines)

        result = f"//PREPEND BEGIN\n{prepend_text}\n//PREPEND END\n\n"
        result += f"//TEMPLATE BEGIN\n{template_text}\n//TEMPLATE END\n\n"
        result += f"//APPEND BEGIN\n{append_text}\n//APPEND END"
        return result

    # For unknown languages, just wrap everything in TEMPLATE
    return f"//PREPEND BEGIN\n\n//PREPEND END\n\n//TEMPLATE BEGIN\n{code}\n//TEMPLATE END\n\n//APPEND BEGIN\n\n//APPEND END"


def _apply_fixes(client: httpx.Client, csrf: str, problem: dict, fixes: dict) -> None:
    """Apply LLM-suggested fixes to a problem via the OJ Admin API."""
    updated = dict(problem)  # shallow copy

    # Apply template fixes — ensure markers are present
    if fixes.get("template"):
        merged_template = dict(updated.get("template") or {})
        for lang, code in fixes["template"].items():
            if code and isinstance(code, str):
                # Auto-wrap bare code into //PREPEND/TEMPLATE/APPEND format
                merged_template[lang] = _ensure_template_markers(code, lang)
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
# Manual batch audit task — for on-demand use via API
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_all_problems",
    bind=True,
    queue="audit",
    soft_time_limit=7200,  # 2 hours soft limit for the full batch
    time_limit=7800,       # 2h10m hard limit
)
def audit_all_problems(self, force: bool = False, limit: int = 0) -> dict:
    """Orchestrate batch audit of all (or all un-audited) problems.

    DISCLAIMER: This task dispatches multiple sub-tasks concurrently.
    For steady background processing, prefer the beat-scheduled
    ``audit_next_problem`` which processes one problem per tick.

    Args:
        force: If True, re-audit all problems regardless of existing records.
        limit: Maximum number of problems to audit. 0 means all (but capped
               at what _fetch_problem_list returns).

    Returns:
        dict with batch_id, total count, and dispatched task IDs.
    """
    batch_id = str(uuid.uuid4())[:8]
    logger.info("Batch audit %s started (force=%s, limit=%s)", batch_id, force, limit)

    # Step 1: Login and fetch problem list
    try:
        client, csrf = _oj_login()
        # When limit is 0 (default), apply a reasonable cap for first run
        effective_limit = limit if limit > 0 else settings.audit_batch_size
        problems = _fetch_problem_list(client, csrf, limit=effective_limit)
    except Exception as exc:
        logger.exception("OJ login/fetch failed for batch audit %s", batch_id)
        raise self.retry(exc=exc)
    finally:
        client.close()

    # Step 2: Filter out already-audited problems (unless force)
    if not force:
        audited_ids = _get_all_audited_ids()
        target_problems = [p for p in problems if p["_id"] not in audited_ids]
        logger.info("Batch %s: %d of %d problems need auditing (already passed: %d)",
                     batch_id, len(target_problems), len(problems), len(audited_ids))
    else:
        target_problems = problems
        logger.info("Batch %s (force): re-auditing %d problems", batch_id, len(target_problems))

    if not target_problems:
        return {
            "batch_id": batch_id,
            "total": len(problems),
            "audited": 0,
            "skipped": len(problems),
            "message": "All problems already audited",
        }

    # Step 3: Dispatch individual audit tasks with rate limiting.
    # We add a countdown between tasks so the GPU isn't overwhelmed.
    # With concurrency=1 and 10min beat interval, this is mainly for manual batch runs.
    task_ids = []
    for i, p in enumerate(target_problems):
        summary = {"_id": p["_id"], "id": p["id"], "title": p.get("title", "")}
        # Stagger tasks: each task starts 10 minutes after the previous one
        countdown = i * 600  # 600 seconds = 10 minutes
        result = audit_single_problem.apply_async(
            args=(summary,),
            queue="audit",
            countdown=countdown,
        )
        task_ids.append(result.id)
        if (i + 1) % 10 == 0:
            logger.info("Batch %s progress: dispatched %d/%d tasks (next in %ds)",
                        batch_id, i + 1, len(target_problems), countdown)

    logger.info("Batch %s: dispatched %d audit tasks (task_ids: %s...)",
                batch_id, len(task_ids), task_ids[:3])

    return {
        "batch_id": batch_id,
        "total": len(problems),
        "dispatched": len(task_ids),
        "skipped": len(problems) - len(target_problems),
        "task_ids": task_ids[:50],  # only return first 50 for safety
    }