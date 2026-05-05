"""Background Celery task: problem quality auditor.

Audits all local (custom-*) OJ problems via Xiaomi MiniMax LLM (mimo-v2-pro),
evaluating completeness, removing non-OJ content, deduplicating garbage,
reclassifying difficulty, and adding algorithmic tags.

Key changes from v2 (Ollama):
- Uses Xiaomi MiniMax API (mimo-v2-pro) instead of local Ollama GPU.
- Direct PostgreSQL queries bypass broken OJ Admin API pagination.
- Beat fires every 100s (3 audits / 5 min).
- Deduplicates boilerplate like "例五、例六", removes non-OJ items.
- Full difficulty reclassification + algorithm tag assignment.
"""
import json
import logging
import re as _re
import uuid
from datetime import datetime, timezone

import httpx

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger("ai-agent-lite.audit")

# All local problem IDs start with this prefix.
LOCAL_PREFIX = "custom-"


# ---------------------------------------------------------------------------
# OJ Admin API helpers (synchronous)
# ---------------------------------------------------------------------------

def _oj_login() -> tuple[httpx.Client, str]:
    """Authenticate with the OJ Admin API and return (client, csrf_token)."""
    client = httpx.Client(base_url=settings.oj_api_url, timeout=30.0)
    r = client.get("/api/profile")
    r.raise_for_status()
    csrf = client.cookies.get("csrftoken", "")
    r = client.post(
        "/api/login",
        json={"username": settings.oj_admin_user, "password": settings.oj_admin_pass},
        headers={"X-CSRFToken": csrf},
    )
    r.raise_for_status()
    csrf = client.cookies.get("csrftoken", csrf)
    logger.info("OJ login succeeded, csrf=%s…", csrf[:8])
    return client, csrf


def _resolve_db_id(client: httpx.Client, csrf: str, display_id: str) -> int:
    r = client.get(
        "/api/admin/problem",
        params={"keyword": display_id, "limit": 10, "page": 1},
        headers={"X-CSRFToken": csrf},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("error") is not None:
        return 0
    for p in data.get("data", {}).get("results", []):
        if p.get("_id") == display_id:
            return p["id"]
    return 0


def _fetch_problem_detail(client: httpx.Client, csrf: str, db_id: int) -> dict | None:
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
    r = client.put(
        "/api/admin/problem",
        json=payload,
        headers={"X-CSRFToken": csrf},
    )
    if r.status_code >= 400:
        logger.error(
            "Problem update failed id=%s status=%d: %s",
            payload.get("_id"), r.status_code, r.text[:300],
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Xiaomi MiniMax LLM call (replaces Ollama)
# ---------------------------------------------------------------------------

def _call_xiaomi(system_prompt: str, user_prompt: str) -> str:
    """Send a completion request to Xiaomi MiniMax API.

    Returns stripped response text. Raises on failure.
    """
    url = settings.xiaomi_api_url
    headers = {
        "Authorization": f"Bearer {settings.xiaomi_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.xiaomi_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,   # deterministic audit
        "max_tokens": 32768,
        "stream": False,
    }
    with httpx.Client(timeout=settings.xiaomi_timeout) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        # Fallback: thinking models put output in reasoning_content
        if not content.strip():
            content = msg.get("reasoning_content", "") or ""
        # Strip markdown fences
        content = _re.sub(r'^```(?:json)?\s*\n?', '', content.strip())
        content = _re.sub(r'\n?```\s*$', '', content)
        return content.strip()


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

_AUDIT_SYSTEM = """You are an expert competitive-programming problem curator and auditor for a university-level Online Judge (OJ).

Your job is to evaluate and FIX a problem JSON. You receive the full database record.
You must do ALL of the following in ONE pass:

## 1. LOCAL-ONLY ID Check
Only problems with `_id` starting with `custom-` are local. Skip others.

## 2. Deduplicate Boilerplate / Garbage
Look for and REMOVE these patterns from `description` / `input_description` / `output_description`:
- Lines like "例五、输入……例六、输出……", "样例五", "例3、", "输入样例5", any numbered examples beyond the first
- Repeated placeholder text like "Button", "???", "暂无"
- HTML residue: `<br>`, `<p>`, `&nbsp;`, `&#039;`
- Any sentence that is NOT part of the actual problem statement

## 3. Non-OJ Content Detection (CRITICAL)
If the problem is NOT an algorithmic/programming problem, flag it as `"status": "remove"` with `"reason"`.
Non-OJ content includes:
- "输出一首古诗" / "打印九九乘法表" / "print a poem"
- Anything asking to output art, poems, ASCII pictures
- Trivial print statements with no algorithmic thinking
- Problems that can be solved with a single `print("...")` without input processing

## 4. Complete Structure Enforcement
Every VALID problem MUST have:
- `title`: clear, no trailing spaces, no NBSP
- `description`: full problem text (story + task), cleaned, >= 50 chars
- `input_description`: input format specification
- `output_description`: output format specification
- `samples`: at least 1 {input, output} pair with real data
- `hint`: optional but encouraged

## 5. Difficulty Reclassification (REQUIRED)
IGNORE the existing `difficulty` field. Re-evaluate based on:
- **Low**: simple arithmetic, conditionals, basic loops, no data structures
- **Mid**: arrays, sorting, greedy, basic DP, binary search, strings, hashing
- **High**: complex DP, graph algorithms (BFS/DFS/Dijkstra/MST), segment trees, advanced math, flow

## 6. Algorithm Tag Assignment (REQUIRED)
Provide at least 1-3 tags from this list (or related terms):
排序, 二分, 搜索, DP/动态规划, 贪心, 图论, 并查集, 最短路, 树, 线段树,
字符串, 哈希, 数学, 数论, 模拟, 枚举, 递归, 回溯, 分治, 前缀和,
差分, 双指针, 滑动窗口, 单调栈, 位运算, 组合数学, 博弈论, 计算几何

## 7. Starter Code Templates (MUST use markers)
For EVERY language (C, C++, Java, Python3), produce or verify templates using:
```
//PREPEND BEGIN
<#include / imports / class opening>
//PREPEND END

//TEMPLATE BEGIN
<solve() with typed params + return type, NO I/O>
//TEMPLATE END

//APPEND BEGIN
<main() reads input, calls solve(), prints return>
//APPEND END
```

CRITICAL RULES:
- All languages use `//` markers (even Python3)
- solve() takes typed parameters, returns value, does NO I/O
- main() reads stdin, calls solve(), prints result
- Template must match the problem's actual input format from `input_description`
- Include `# Example: solve(arg1, arg2) -> expected_output`

## 8. Metadata
- `source`: leave as-is unless empty, then set to "CDUT OJ"
- `languages`: must include ["C","C++","Java","Python3"]
- `time_limit` and `memory_limit`: keep existing

## Response Format
Output ONLY this JSON, no markdown fences, no text before/after:

{
  "status": "pass|fail|remove",
  "reason": "if remove: why this is not an OJ problem",
  "issues": ["list of specific issues found, empty if pass"],
  "fixes": {
    "title": "cleaned title or null",
    "description": "cleaned description with garbage removed or null",
    "input_description": "cleaned or null",
    "output_description": "cleaned or null",
    "hint": "hint text or null",
    "samples": [{"input": "...", "output": "..."}],
    "difficulty": "Low|Mid|High",
    "tags": ["tag1", "tag2", "tag3"],
    "source": "CDUT OJ or existing",
    "template": {
      "C": "full C template with //PREPEND/TEMPLATE/APPEND markers or null",
      "C++": "full C++ template with markers or null",
      "Java": "full Java template with markers or null",
      "Python3": "full Python3 template with markers or null"
    }
  }
}

If status is "pass", put nulls in fixes. If "remove", fixes can be empty.
For "fail", provide corrections for every issue found.
"""


def _build_audit_prompt(problem: dict) -> str:
    """Build user prompt with the problem data."""
    problem_data = json.dumps(problem, ensure_ascii=False, indent=2)
    return f"Audit the following problem:\n\n{problem_data}"


# ---------------------------------------------------------------------------
# PostgreSQL direct helpers (bypasses broken OJ API pagination)
# ---------------------------------------------------------------------------

# In-memory dedup: prevent a Beat tick from picking the same problem that
# the previous tick's task hasn't finished writing to the DB yet.
_in_flight_ids: set[str] = set()


def _pg_connect():
    """Return a psycopg2 connection to the OJ database."""
    import psycopg2
    db_url = settings.db_url.replace("+asyncpg", "")
    return psycopg2.connect(db_url)


def _get_all_audited_ids() -> set[str]:
    """Return set of local problem display_ids that already have an audit record."""
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT problem_display_id FROM {schema}.problem_audit "
                "WHERE status = 'pass'".format(schema=settings.db_schema),
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def _get_next_local_unaudited() -> dict | None:
    """Find ONE local (custom-*) problem not yet audited, via PostgreSQL.

    Returns dict {id, _id, title} or None if all local problems are audited.
    Excludes ids in the in-memory _in_flight_ids set to avoid double-audit.
    """
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            # Build dynamic NOT IN for in-flight ids
            in_flight_clause = ""
            in_flight_params = ()
            if _in_flight_ids:
                placeholders = ",".join(["%s"] * len(_in_flight_ids))
                in_flight_clause = f"AND p._id NOT IN ({placeholders})"
                in_flight_params = tuple(sorted(_in_flight_ids))

            cur.execute("""
                SELECT p.id, p._id, p.title
                FROM problem p
                WHERE p._id LIKE 'custom-%%'
                  AND p._id NOT IN (
                      SELECT problem_display_id
                      FROM {schema}.problem_audit
                  )
                  {in_flight}
                ORDER BY p.id
                LIMIT 1
            """.format(
                schema=settings.db_schema,
                in_flight=in_flight_clause,
            ), in_flight_params)
            row = cur.fetchone()
            if row:
                return {"id": row[0], "_id": row[1], "title": row[2]}
            return None
    finally:
        conn.close()


def _get_all_local_problems() -> list[dict]:
    """Return ALL local problems (id, _id, title) via PostgreSQL."""
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, _id, title FROM problem WHERE _id LIKE 'custom-%%' ORDER BY id"
            )
            return [{"id": r[0], "_id": r[1], "title": r[2]} for r in cur.fetchall()]
    finally:
        conn.close()


def _get_local_problem_count() -> int:
    """Count how many local (custom-*) problems exist."""
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM problem WHERE _id LIKE 'custom-%%'")
            return cur.fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _upsert_audit_record(
    display_id: str,
    db_id: int,
    audit_status: str,
    issues: list,
    fixes: dict,
    llm_raw: str,
    extra: dict | None = None,
) -> None:
    """Insert or update an audit record."""
    import psycopg2
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM {schema}.problem_audit WHERE problem_display_id = %s "
                "ORDER BY created_at DESC LIMIT 1".format(schema=settings.db_schema),
                (display_id,),
            )
            existing = cur.fetchone()

            now = datetime.now(timezone.utc)
            issues_j = json.dumps(issues, ensure_ascii=False)
            fixes_j = json.dumps(fixes, ensure_ascii=False)

            if existing:
                cur.execute(
                    "UPDATE {schema}.problem_audit SET "
                    "status=%s, issues=%s, fixes=%s, llm_raw_response=%s, "
                    "updated_at=%s WHERE id=%s".format(schema=settings.db_schema),
                    (audit_status, issues_j, fixes_j, llm_raw, now, existing[0]),
                )
            else:
                cur.execute(
                    "INSERT INTO {schema}.problem_audit "
                    "(problem_display_id, problem_db_id, status, issues, fixes, "
                    "llm_raw_response, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)".format(
                        schema=settings.db_schema
                    ),
                    (display_id, db_id, audit_status,
                     issues_j, fixes_j, llm_raw, now, now),
                )
            conn.commit()
    finally:
        conn.close()


def _delete_audit_record(display_id: str) -> None:
    """Remove all audit records for a problem (allows re-audit)."""
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM {schema}.problem_audit WHERE problem_display_id = %s".format(
                    schema=settings.db_schema
                ),
                (display_id,),
            )
            conn.commit()
    finally:
        conn.close()


def _clear_all_audit_records() -> int:
    """Delete ALL audit records. Returns count of deleted rows."""
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM {schema}.problem_audit".format(schema=settings.db_schema)
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Quick pre-check
# ---------------------------------------------------------------------------

def _quick_check_problem(problem: dict) -> list[str]:
    """Fast heuristic pre-check."""
    issues = []
    if not problem.get("title") or not problem["title"].strip():
        issues.append("Missing or empty title")
    desc = problem.get("description") or ""
    if not desc.strip() or len(desc.strip()) < 10:
        issues.append("Description too short or empty")
    samples = problem.get("samples") or []
    if not samples:
        issues.append("No sample input/output")
    template = problem.get("template") or {}
    for lang in ("C", "C++", "Java", "Python3"):
        code = template.get(lang, "") or ""
        if not code.strip():
            issues.append(f"Missing starter code for {lang}")
        elif "//TEMPLATE BEGIN" not in code:
            issues.append(f"Starter code lacks markers for {lang}")
        elif _re.search(r'void\s+solve\s*\(\s*(void)?\s*\)', code):
            issues.append(
                f"void solve(void) in {lang} — solve() must take params and return result"
            )
    if not (problem.get("test_case_id") or "").strip():
        issues.append("Empty test_case_id")
    return issues


# ---------------------------------------------------------------------------
# DEFAULT_TEMPLATES (fallback)
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATES = {
    "C": (
        "//PREPEND BEGIN\n"
        "#include <stdio.h>\n"
        "//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "int solve(int n) {\n"
        "    // TODO: implement and return result\n"
        "    return 0;\n"
        "}\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "int main(void) {\n"
        "    int n; scanf(\"%d\", &n);\n"
        "    printf(\"%d\\n\", solve(n));\n"
        "    return 0;\n"
        "}\n"
        "//APPEND END\n"
    ),
    "C++": (
        "//PREPEND BEGIN\n"
        "#include <bits/stdc++.h>\n"
        "using namespace std;\n"
        "//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "int solve(int n) {\n"
        "    // TODO: implement and return result\n"
        "    return 0;\n"
        "}\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "int main() {\n"
        "    ios::sync_with_stdio(false); cin.tie(nullptr);\n"
        "    int n; cin >> n;\n"
        "    cout << solve(n) << endl; return 0;\n"
        "}\n"
        "//APPEND END\n"
    ),
    "Java": (
        "//PREPEND BEGIN\n"
        "import java.util.*;\n\n"
        "public class Main {\n"
        "//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "    public static int solve(int n) {\n"
        "        // TODO: implement and return result\n"
        "        return 0;\n"
        "    }\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        int n = sc.nextInt();\n"
        "        System.out.println(solve(n));\n"
        "    }\n"
        "}\n"
        "//APPEND END\n"
    ),
    "Python3": (
        "//PREPEND BEGIN\n\n//PREPEND END\n\n"
        "//TEMPLATE BEGIN\n"
        "def solve(n: int) -> int:\n"
        "    # TODO: implement and return result\n"
        "    return 0\n\n"
        "//TEMPLATE END\n\n"
        "//APPEND BEGIN\n"
        "if __name__ == '__main__':\n"
        "    n = int(input())\n"
        "    print(solve(n))\n"
        "//APPEND END\n"
    ),
}


# ---------------------------------------------------------------------------
# Ensure marker format
# ---------------------------------------------------------------------------

def _ensure_template_markers(code: str, lang: str) -> str:
    """Wrap bare code into QDUOJ's //PREPEND/TEMPLATE/APPEND marker format."""
    if "//TEMPLATE BEGIN" in code:
        return code

    lines = code.split("\n")

    if lang == "Python3":
        prepend_lines = []
        template_lines = []
        append_lines = []
        in_append = False

        for line in lines:
            s = line.strip()
            if s.startswith("if __name__") or s == "if __name__ == '__main__':":
                in_append = True
                append_lines.append(line)
                continue
            if in_append:
                append_lines.append(line)
                continue
            if s in ("import sys",) or s.startswith("import sys #"):
                continue
            if not template_lines and s.startswith("def solve"):
                template_lines.append(line)
                continue
            if template_lines:
                template_lines.append(line)
            else:
                prepend_lines.append(line)

        pre = "\n".join(prepend_lines).strip()
        tpl = "\n".join(template_lines)
        app = "\n".join(append_lines)
        return (
            f"//PREPEND BEGIN\n{pre}\n//PREPEND END\n\n"
            f"//TEMPLATE BEGIN\n{tpl}\n//TEMPLATE END\n\n"
            f"//APPEND BEGIN\n{app}\n//APPEND END"
        )

    elif lang in ("C", "C++"):
        prepend_lines, template_lines, append_lines = [], [], []
        in_append = False
        for line in lines:
            s = line.strip()
            if s.startswith("int main("):
                in_append = True
                append_lines.append(line)
                continue
            if in_append:
                append_lines.append(line)
                continue
            if not template_lines and (s.startswith("void solve") or s.startswith("int solve")):
                template_lines.append(line)
                continue
            if template_lines:
                template_lines.append(line)
            else:
                prepend_lines.append(line)

        pre = "\n".join(prepend_lines)
        tpl = "\n".join(template_lines)
        app = "\n".join(append_lines)
        return (
            f"//PREPEND BEGIN\n{pre}\n//PREPEND END\n\n"
            f"//TEMPLATE BEGIN\n{tpl}\n//TEMPLATE END\n\n"
            f"//APPEND BEGIN\n{app}\n//APPEND END"
        )

    elif lang == "Java":
        prepend_lines, template_lines, append_lines = [], [], []
        in_template, in_append, depth = False, False, 0
        for line in lines:
            s = line.strip()
            if s.startswith("public static") and "solve" in s:
                in_template = True
                depth = 0
                template_lines.append(line)
                depth += line.count("{") - line.count("}")
                continue
            if in_template and not in_append:
                template_lines.append(line)
                depth += line.count("{") - line.count("}")
                if depth <= 0 and "{" in "".join(template_lines):
                    in_template = False
                continue
            if s.startswith("public static void main"):
                in_append = True
            if in_append:
                append_lines.append(line)
            else:
                prepend_lines.append(line)

        pre = "\n".join(prepend_lines)
        tpl = "\n".join(template_lines)
        app = "\n".join(append_lines)
        return (
            f"//PREPEND BEGIN\n{pre}\n//PREPEND END\n\n"
            f"//TEMPLATE BEGIN\n{tpl}\n//TEMPLATE END\n\n"
            f"//APPEND BEGIN\n{app}\n//APPEND END"
        )

    # unknown: everything in TEMPLATE
    return (
        "//PREPEND BEGIN\n\n//PREPEND END\n\n"
        f"//TEMPLATE BEGIN\n{code}\n//TEMPLATE END\n\n"
        "//APPEND BEGIN\n\n//APPEND END"
    )


# ---------------------------------------------------------------------------
# Fix application
# ---------------------------------------------------------------------------

def _apply_fixes(client: httpx.Client, csrf: str, problem: dict, fixes: dict) -> None:
    """Apply LLM-suggested fixes via the OJ Admin API."""
    updated = dict(problem)

    if fixes.get("template"):
        merged = dict(updated.get("template") or {})
        for lang, code in fixes["template"].items():
            if code and isinstance(code, str):
                merged[lang] = _ensure_template_markers(code, lang)
        for lang in ("C", "C++", "Java", "Python3"):
            if lang not in fixes["template"] or not fixes["template"].get(lang):
                existing = merged.get(lang, "") or ""
                if existing.strip() and "//TEMPLATE BEGIN" not in existing:
                    merged[lang] = _ensure_template_markers(existing, lang)
        updated["template"] = merged

    for field in ("title", "description", "input_description", "output_description", "hint"):
        if fixes.get(field):
            updated[field] = fixes[field]

    if fixes.get("samples"):
        updated["samples"] = fixes["samples"]

    if fixes.get("difficulty"):
        updated["difficulty"] = fixes["difficulty"]
    if fixes.get("source"):
        updated["source"] = fixes["source"]
    if fixes.get("tags"):
        updated["tags"] = fixes["tags"]

    for required in ("_id", "id", "test_case_id", "io_mode", "languages",
                     "rule_type", "spj", "visible"):
        if required not in updated and required in problem:
            updated[required] = problem[required]

    ok = _update_problem(client, csrf, updated)
    if not ok:
        raise RuntimeError(f"PUT /api/admin/problem failed for _id={updated.get('_id')}")


# ---------------------------------------------------------------------------
# Parse LLM JSON response
# ---------------------------------------------------------------------------

def _parse_llm_response(raw: str) -> dict:
    """Extract JSON from LLM response."""
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            result = json.loads(raw[start:end])
            if "status" in result:
                return result
        except json.JSONDecodeError:
            pass
    logger.warning("LLM response was not valid JSON; raw preview: %s", raw[:200])
    return {"status": "error", "issues": ["LLM response was not valid JSON"], "fixes": {}}


# ---------------------------------------------------------------------------
# Core audit task — exactly ONE problem
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_single_problem",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="audit",
    soft_time_limit=300,
    time_limit=360,
)
def audit_single_problem(self, problem_summary: dict) -> dict:
    """Audit a single problem via Xiaomi LLM and auto-fix if needed."""
    display_id = problem_summary["_id"]
    db_id = problem_summary.get("id", 0)
    title = problem_summary.get("title", display_id)

    if db_id == 0:
        try:
            client, csrf = _oj_login()
            db_id = _resolve_db_id(client, csrf, display_id)
            if db_id:
                detail = _fetch_problem_detail(client, csrf, db_id)
                title = (detail or {}).get("title") or display_id
                logger.info("Resolved display_id=%s -> db_id=%d", display_id, db_id)
            else:
                logger.error("Cannot resolve db_id for display_id=%s", display_id)
                return {"_id": display_id, "status": "error", "message": "Not found in OJ list"}
        except Exception as exc:
            logger.error("Failed to resolve db_id for %s: %s", display_id, exc)
            return {"_id": display_id, "status": "error", "message": f"resolve: {exc}"}

    return _do_audit_problem(display_id, db_id, title, retry=self)


def _do_audit_problem(
    display_id: str, db_id: int, title: str, retry=None,
) -> dict:
    """Core audit logic."""
    logger.info("Auditing _id=%s (db_id=%d, title=%s)", display_id, db_id, title)

    client = None
    try:
        client, csrf = _oj_login()
        problem = _fetch_problem_detail(client, csrf, db_id)
        if problem is None:
            return {"_id": display_id, "status": "error", "message": "Failed to fetch detail"}
    except Exception as exc:
        logger.exception("OJ login/fetch failed _id=%s", display_id)
        if retry:
            raise retry.retry(exc=exc)
        raise

    try:
        prompt = _build_audit_prompt(problem)
        try:
            raw = _call_xiaomi(_AUDIT_SYSTEM, prompt)
        except Exception as exc:
            logger.exception("Xiaomi API call failed _id=%s", display_id)
            if retry:
                raise retry.retry(exc=exc)
            raise

        result = _parse_llm_response(raw)

        status = result.get("status", "error")
        issues = result.get("issues", [])
        fixes = result.get("fixes", {}) or {}

        if status == "remove":
            reason = result.get("reason", "Non-OJ problem")
            logger.info("REMOVE %s: %s", display_id, reason)
            _upsert_audit_record(display_id, db_id, "remove", [reason], {}, raw)
            return {
                "_id": display_id, "status": "remove",
                "issues": [reason],
            }

        _upsert_audit_record(display_id, db_id, status, issues, fixes, raw)

        if status == "fail" and fixes:
            try:
                _apply_fixes(client, csrf, problem, fixes)
                logger.info("Auto-fixed _id=%s", display_id)
            except Exception:
                logger.exception("Auto-fix failed _id=%s", display_id)
                _upsert_audit_record(display_id, db_id, "fix_failed", issues, fixes, raw)

        return {"_id": display_id, "status": status, "issues": issues}
    finally:
        if client:
            client.close()


# ---------------------------------------------------------------------------
# Beat-scheduled task: audit ONE local problem per tick (every 100s)
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_next_problem",
    queue="audit",
    soft_time_limit=300,
    time_limit=360,
)
def audit_next_problem() -> dict:
    """Find and audit ONE un-audited local problem via PostgreSQL.

    Beat fires every 100s, so ~3 audits / 5 min.
    Uses _in_flight_ids to prevent double-audit from overlapping ticks.
    """
    problem = _get_next_local_unaudited()
    if problem is None:
        logger.info("No un-audited local problems — all done")
        return {"status": "no_work", "message": "All local problems audited"}

    display_id = problem["_id"]
    db_id = problem["id"]
    title = problem.get("title", display_id)

    # Mark as in-flight before audit starts
    _in_flight_ids.add(display_id)
    try:
        logger.info("Beat tick: auditing _id=%s (db_id=%d)", display_id, db_id)
        return _do_audit_problem(display_id, db_id, title)
    finally:
        _in_flight_ids.discard(display_id)


# ---------------------------------------------------------------------------
# Batch audit (on-demand via API)
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.audit_all_problems",
    bind=True,
    queue="audit",
    soft_time_limit=7200,
    time_limit=7800,
)
def audit_all_problems(self, force: bool = False, limit: int = 0) -> dict:
    """Orchestrate batch audit of all local problems.

    Uses PostgreSQL to list local problems, dispatches staggered sub-tasks.
    """
    batch_id = str(uuid.uuid4())[:8]
    logger.info("Batch %s started (force=%s, limit=%s)", batch_id, force, limit)

    all_local = _get_all_local_problems()
    logger.info("Batch %s: %d local problems total", batch_id, len(all_local))

    if not force:
        audited = _get_all_audited_ids()
        targets = [p for p in all_local if p["_id"] not in audited]
        logger.info("Batch %s: %d need auditing (already passed: %d)",
                     batch_id, len(targets), len(audited))
    else:
        targets = all_local

    if limit > 0 and len(targets) > limit:
        targets = targets[:limit]

    if not targets:
        return {
            "batch_id": batch_id, "total": len(all_local),
            "dispatched": 0, "message": "All local problems already audited",
        }

    task_ids = []
    for i, p in enumerate(targets):
        summary = {"_id": p["_id"], "id": p["id"], "title": p.get("title", "")}
        countdown = i * 110  # ~110s stagger
        r = audit_single_problem.apply_async(args=(summary,), queue="audit", countdown=countdown)
        task_ids.append(r.id)

    logger.info("Batch %s: dispatched %d tasks", batch_id, len(task_ids))
    return {
        "batch_id": batch_id, "total": len(all_local),
        "dispatched": len(task_ids),
        "task_ids": task_ids[:50],
    }


# ---------------------------------------------------------------------------
# Admin: force-clear all audit records and restart
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.problem_auditor.reset_audit_state",
    queue="audit",
)
def reset_audit_state() -> dict:
    """Clear all audit records so everything gets re-audited."""
    deleted = _clear_all_audit_records()
    total = _get_local_problem_count()
    return {
        "deleted_records": deleted,
        "local_problems": total,
        "message": f"Cleared {deleted} records. {total} local problems ready for re-audit.",
    }
