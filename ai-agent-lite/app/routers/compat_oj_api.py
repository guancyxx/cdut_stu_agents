"""QDUOJ-compatible API surface backed by ai-agent-lite data stores.

Provides minimal endpoints required by current frontend:
- GET /api/profile
- GET /api/captcha
- POST /api/login
- POST /api/register
- POST /api/logout
- GET /api/problem/
- GET /api/submissions
- POST /api/submission
- GET /api/submission
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.database import async_session
from app.services.judge_service import SandboxClient, judge_submission

router = APIRouter(prefix="/api", tags=["compat-oj-api"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PEPPER = os.getenv("LITE_AUTH_PEPPER", "cdut-lite-pepper")


def _hash_password(raw: str) -> str:
    """Generate Django-compatible PBKDF2-SHA256 hash string."""
    iterations = 260000
    salt = secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), iterations)
    digest = base64.b64encode(dk).decode("ascii").strip()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _verify_password(raw: str, stored: str) -> bool:
    """Verify both legacy pepper-sha256 and Django pbkdf2 hashes."""
    if not stored:
        return False

    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iter_str, salt, digest = stored.split("$", 3)
            iterations = int(iter_str)
            dk = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), iterations)
            calc = base64.b64encode(dk).decode("ascii").strip()
            return hmac.compare_digest(calc, digest)
        except Exception:
            return False

    payload = f"{PEPPER}:{raw}".encode("utf-8")
    return hmac.compare_digest(hashlib.sha256(payload).hexdigest(), stored)


def _status_code_from_verdict(verdict: str) -> int:
    # Legacy-OJ-compatible status codes used by frontend map
    mapping = {
        "AC": 0,
        "WA": -1,
        "CE": -2,
        "TLE": 1,
        "MLE": 3,
        "RE": 4,
        "SE": 5,
    }
    return mapping.get(verdict, 5)


def _status_label(verdict: str) -> str:
    mapping = {
        "AC": "ACCEPTED",
        "WA": "WRONG_ANSWER",
        "CE": "COMPILE_ERROR",
        "TLE": "CPU_TIME_LIMIT_EXCEEDED",
        "MLE": "MEMORY_LIMIT_EXCEEDED",
        "RE": "RUNTIME_ERROR",
        "SE": "SYSTEM_ERROR",
    }
    return mapping.get(verdict, "SYSTEM_ERROR")


def _parse_json(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return default
    return default


def _current_username(request: Request) -> str | None:
    return request.cookies.get("lite_user")


def _parse_uuid(value: str) -> str | None:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _contest_status(start_time: datetime, end_time: datetime, now: datetime) -> str:
    if now < start_time:
        return "upcoming"
    if now >= end_time:
        return "ended"
    return "running"


async def _ensure_contest_schema() -> None:
    async with async_session() as db:
        await db.execute(text("CREATE SCHEMA IF NOT EXISTS ai_agent"))
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ai_agent.contests (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    title varchar(255) NOT NULL,
                    description text,
                    start_time timestamptz NOT NULL,
                    end_time timestamptz NOT NULL,
                    status varchar(16) NOT NULL DEFAULT 'upcoming',
                    created_by varchar(64) NOT NULL,
                    created_at timestamptz NOT NULL,
                    updated_at timestamptz NOT NULL
                )
                """
            )
        )
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ai_agent.contest_problems (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    contest_id uuid NOT NULL REFERENCES ai_agent.contests(id) ON DELETE CASCADE,
                    problem_id varchar(64) NOT NULL,
                    display_order integer NOT NULL DEFAULT 0,
                    UNIQUE (contest_id, problem_id)
                )
                """
            )
        )
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ai_agent.contest_participants (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    contest_id uuid NOT NULL REFERENCES ai_agent.contests(id) ON DELETE CASCADE,
                    user_id varchar(64) NOT NULL,
                    joined_at timestamptz NOT NULL,
                    UNIQUE (contest_id, user_id)
                )
                """
            )
        )
        await db.execute(
            text(
                "ALTER TABLE ai_agent.submissions "
                "ADD COLUMN IF NOT EXISTS contest_id uuid NULL"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE ai_agent.submissions "
                "ADD COLUMN IF NOT EXISTS is_contest boolean NOT NULL DEFAULT false"
            )
        )
        await db.execute(
            text(
                "ALTER TABLE ai_agent.contests "
                "ADD COLUMN IF NOT EXISTS visible boolean NOT NULL DEFAULT true"
            )
        )
        await db.commit()


async def _require_admin_username(request: Request) -> str:
    username = _current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Please login first")

    async with async_session() as db:
        row = (
            await db.execute(
                text("SELECT COALESCE(admin_type,0) FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": username},
            )
        ).fetchone()

    if not row or int(row[0] or 0) < 1:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return username


def _captcha_svg_data_url() -> str:
    """Generate a visible inline SVG captcha data URL for compat UI."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    captcha_text = "".join(secrets.choice(alphabet) for _ in range(4))

    noise = "".join(
        f'<line x1="{i * 17 + 8}" y1="6" x2="{(i + 1) * 19}" y2="38" stroke="#9ca3af" stroke-width="1" opacity="0.35" />'
        for i in range(3)
    )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="44" viewBox="0 0 100 44">'
        '<rect width="100" height="44" rx="6" fill="#111827" />'
        f'{noise}'
        f'<text x="50" y="29" text-anchor="middle" fill="#f9fafb" '
        'font-family="monospace" font-size="22" font-weight="700" letter-spacing="3">'
        f'{captcha_text}'
        '</text>'
        '</svg>'
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


@router.get("/captcha")
async def captcha(response: Response):
    # Frontend register flow expects an image data URL.
    response.set_cookie("csrftoken", "lite-csrf-token", httponly=False, samesite="lax")
    return {"error": None, "data": _captcha_svg_data_url()}


@router.get("/profile")
async def profile(request: Request, response: Response):
    username = _current_username(request)
    response.set_cookie("csrftoken", "lite-csrf-token", httponly=False, samesite="lax")
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "SELECT username, COALESCE(email,''), COALESCE(student_number,''), COALESCE(admin_type,0), COALESCE(password_hash,'') "
                    "FROM ai_agent.local_users WHERE username=:u LIMIT 1"
                ),
                {"u": username},
            )
        ).fetchone()

    if not row:
        return {"error": "Please login first", "data": "Please login first"}

    return {
        "error": None,
        "data": {
            "username": row[0],
            "profile_name": row[0],
            "email": row[1],
            "student_number": row[2],
            "admin_type": int(row[3] or 0),
            "admin_type_name": "Super Admin" if int(row[3] or 0) == 2 else ("Admin" if int(row[3] or 0) == 1 else "Regular User"),
        },
    }


@router.post("/register")
async def register(response: Response, payload: dict = Body(...)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    email = str(payload.get("email", "")).strip()
    student_number = str(payload.get("student_number", "")).strip()

    if not USERNAME_RE.match(username):
        return {"error": "Invalid username", "data": "Invalid username"}
    if len(password) < 6:
        return {"error": "Invalid password", "data": "Invalid password"}
    if email and not EMAIL_RE.match(email):
        return {"error": "Invalid email", "data": "Invalid email"}

    async with async_session() as db:
        exists = (
            await db.execute(
                text("SELECT 1 FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": username},
            )
        ).fetchone()
        if exists:
            return {"error": "Username already exists", "data": "Username already exists"}

        await db.execute(
            text(
                "INSERT INTO ai_agent.local_users (username, password_hash, email, student_number, admin_type, created_at, updated_at) "
                "VALUES (:u, :p, :e, :s, 0, :now, :now)"
            ),
            {
                "u": username,
                "p": _hash_password(password),
                "e": email or None,
                "s": student_number or None,
                "now": datetime.now(timezone.utc),
            },
        )
        await db.commit()

    response.set_cookie("lite_user", username, httponly=True, samesite="lax")
    response.set_cookie("csrftoken", "lite-csrf-token", httponly=False, samesite="lax")
    return {"error": None, "data": {"username": username}}


@router.post("/login")
async def login(response: Response, payload: dict = Body(...)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "SELECT username, password_hash FROM ai_agent.local_users "
                    "WHERE username=:u LIMIT 1"
                ),
                {"u": username},
            )
        ).fetchone()

    if not row or not _verify_password(password, str(row[1] or "")):
        return {"error": "Invalid username or password", "data": "Invalid username or password"}

    response.set_cookie("lite_user", username, httponly=True, samesite="lax")
    response.set_cookie("csrftoken", "lite-csrf-token", httponly=False, samesite="lax")
    return {"error": None, "data": {"username": username}}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("lite_user")
    return {"error": None, "data": "ok"}


@router.get("/problem/")
async def list_or_get_problem(
    problem_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    limit: int = Query(default=21, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    async with async_session() as db:
        if problem_id:
            row = (
                await db.execute(
                    text(
                        "SELECT id,_id,title,description,input_description,output_description,samples,hint,source,difficulty,time_limit,memory_limit,languages,template "
                        "FROM problem WHERE _id=:pid OR CAST(id AS TEXT)=:pid LIMIT 1"
                    ),
                    {"pid": problem_id},
                )
            ).fetchone()
            if not row:
                return {"error": "Problem not found", "data": "Problem not found"}
            return {
                "error": None,
                "data": {
                    "id": row[0],
                    "_id": row[1],
                    "title": row[2],
                    "description": row[3] or "",
                    "input_description": row[4] or "",
                    "output_description": row[5] or "",
                    "samples": _parse_json(row[6], []),
                    "hint": row[7] or "",
                    "source": row[8] or "",
                    "difficulty": row[9] or "Low",
                    "time_limit": int(row[10] or 1000),
                    "memory_limit": int(row[11] or 256),
                    "languages": _parse_json(row[12], ["C", "C++", "Java", "Python3"]),
                    "template": _parse_json(row[13], {}),
                },
            }

        where = ["1=1"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if keyword:
            where.append("(title ILIKE :kw OR _id ILIKE :kw)")
            params["kw"] = f"%{keyword.strip()}%"
        if difficulty in {"Low", "Mid", "High"}:
            where.append("difficulty = :diff")
            params["diff"] = difficulty

        where_sql = " AND ".join(where)
        total = (
            await db.execute(text(f"SELECT COUNT(*) FROM problem WHERE {where_sql}"), params)
        ).scalar_one()

        rows = (
            await db.execute(
                text(
                    f"SELECT id,_id,title,difficulty,time_limit,memory_limit "
                    f"FROM problem WHERE {where_sql} ORDER BY id DESC LIMIT :limit OFFSET :offset"
                ),
                params,
            )
        ).fetchall()

    results = [
        {
            "id": r[0],
            "_id": r[1],
            "title": r[2],
            "difficulty": r[3] or "Low",
            "time_limit": int(r[4] or 1000),
            "memory_limit": int(r[5] or 256),
        }
        for r in rows
    ]
    return {"error": None, "data": {"results": results, "total": int(total)}}


@router.get("/submissions")
async def list_submissions(
    request: Request,
    problem_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
):
    username = _current_username(request) or "anonymous"
    offset = (page - 1) * limit
    resolved_problem_id = problem_id

    async with async_session() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id, problem_id, user_id, verdict, time_sec, memory_kb, compile_error, test_case_results, created_at "
                    "FROM ai_agent.submissions "
                    "WHERE user_id=:u "
                    + ("AND problem_id=:pid " if resolved_problem_id else "")
                    + "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
                ),
                {
                    "u": username,
                    "pid": resolved_problem_id,
                    "limit": limit,
                    "offset": offset,
                }
                if resolved_problem_id
                else {"u": username, "limit": limit, "offset": offset},
            )
        ).fetchall()

    results = []
    for r in rows:
        verdict = str(r[3] or "SE")
        code = _status_code_from_verdict(verdict)
        tc = _parse_json(r[7], [])
        info_data = []
        for case in tc if isinstance(tc, list) else []:
            info_data.append(
                {
                    "test_case": int(case.get("case_index", 0)),
                    "result": _status_code_from_verdict(str(case.get("verdict", "SE"))),
                    "cpu_time": int(float(case.get("time_sec", 0)) * 1000),
                    "memory": int(case.get("max_rss_kb", 0) or 0) * 1024,
                    "score": 0,
                    "output": case.get("stdout", ""),
                }
            )

        results.append(
            {
                "id": str(r[0]),
                "problem_id": r[1],
                "username": r[2],
                "result": code,
                "statistic_info": {
                    "score": 100 if verdict == "AC" else 0,
                    "time_cost": int(float(r[4] or 0) * 1000),
                    "memory_cost": int(r[5] or 0),
                    "err_info": r[6] or "",
                },
                "info": {"err": r[6] or "", "data": info_data},
                "created_at": r[8].isoformat() if r[8] else "",
            }
        )

    return {"error": None, "data": {"results": results}}


@router.post("/submission")
async def submit_code_compat(request: Request, payload: dict = Body(...)):
    await _ensure_contest_schema()
    username = _current_username(request) or "anonymous"
    problem_id = str(payload.get("problem_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    code = str(payload.get("code", ""))
    contest_id_raw = payload.get("contest_id")

    if not problem_id or not language or not code:
        return {"error": "Invalid payload", "data": "Invalid payload"}

    parsed_contest_id = _parse_uuid(contest_id_raw) if contest_id_raw else None
    is_contest = bool(parsed_contest_id)

    if is_contest:
        async with async_session() as db:
            contest = (
                await db.execute(
                    text(
                        "SELECT id,start_time,end_time FROM ai_agent.contests "
                        "WHERE id=:contest_id LIMIT 1"
                    ),
                    {"contest_id": parsed_contest_id},
                )
            ).fetchone()

            if not contest:
                return {"error": "Contest not found", "data": "Contest not found"}

            now = _utc_now()
            if _contest_status(contest[1], contest[2], now) != "running":
                return {"error": "Contest is not running", "data": "Contest is not running"}

            joined = (
                await db.execute(
                    text(
                        "SELECT 1 FROM ai_agent.contest_participants "
                        "WHERE contest_id=:contest_id AND user_id=:user_id LIMIT 1"
                    ),
                    {"contest_id": parsed_contest_id, "user_id": username},
                )
            ).fetchone()
            if not joined:
                return {"error": "Please join contest first", "data": "Please join contest first"}

            contest_problem = (
                await db.execute(
                    text(
                        "SELECT 1 FROM ai_agent.contest_problems "
                        "WHERE contest_id=:contest_id AND problem_id=:problem_id LIMIT 1"
                    ),
                    {"contest_id": parsed_contest_id, "problem_id": problem_id},
                )
            ).fetchone()
            if not contest_problem:
                return {"error": "Problem not in contest", "data": "Problem not in contest"}

    # Convert frontend labels to judge labels
    lang_map = {"C++": "cpp", "C": "c", "Java": "java", "Python3": "python3", "cpp": "cpp", "c": "c", "java": "java", "python3": "python3"}
    normalized_lang = lang_map.get(language, language)

    sandbox = SandboxClient()
    if not await sandbox.health():
        raise HTTPException(status_code=503, detail="Sandbox unavailable")

    result = await judge_submission(
        code=code,
        language=normalized_lang,
        problem_id=problem_id,
        sandbox=sandbox,
        user_id=username,
    )

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "INSERT INTO ai_agent.submissions (id,problem_id,user_id,language,code,verdict,time_sec,memory_kb,test_case_results,compile_error,contest_id,is_contest,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),:pid,:uid,:lang,:code,:verdict,:time,:mem,CAST(:tcr AS jsonb),:ce,:contest_id,:is_contest,:now,:now) RETURNING id"
                ),
                {
                    "pid": problem_id,
                    "uid": username,
                    "lang": normalized_lang,
                    "code": code,
                    "verdict": result.verdict,
                    "time": float(result.total_time_sec or 0),
                    "mem": int(result.max_rss_kb or 0),
                    "tcr": json.dumps(result.test_case_results or [], ensure_ascii=False),
                    "ce": result.compile_error or "",
                    "contest_id": parsed_contest_id,
                    "is_contest": is_contest,
                    "now": _utc_now(),
                },
            )
        ).fetchone()
        await db.commit()

    return {"error": None, "data": {"submission_id": str(row[0])}}


@router.get("/submission")
async def submission_detail(
    submission_id: str | None = Query(default=None, alias="id"),
):
    if not submission_id:
        return {"error": "id is required", "data": "id is required"}

    async with async_session() as db:
        r = (
            await db.execute(
                text(
                    "SELECT id, problem_id, verdict, time_sec, memory_kb, compile_error, test_case_results "
                    "FROM ai_agent.submissions WHERE CAST(id AS TEXT)=:sid LIMIT 1"
                ),
                {"sid": submission_id},
            )
        ).fetchone()

    if not r:
        return {"error": "Submission not found", "data": "Submission not found"}

    verdict = str(r[2] or "SE")
    tcr = _parse_json(r[6], [])
    info_data = []
    for case in tcr if isinstance(tcr, list) else []:
        info_data.append(
            {
                "test_case": int(case.get("case_index", 0)),
                "result": _status_code_from_verdict(str(case.get("verdict", "SE"))),
                "cpu_time": int(float(case.get("time_sec", 0)) * 1000),
                "memory": int(case.get("max_rss_kb", 0) or 0) * 1024,
                "score": 0,
                "output": case.get("stdout", ""),
            }
        )

    detail = {
        "id": str(r[0]),
        "problem": r[1],
        "result": _status_code_from_verdict(verdict),
        "statistic_info": {
            "score": 100 if verdict == "AC" else 0,
            "time_cost": int(float(r[3] or 0) * 1000),
            "memory_cost": int(r[4] or 0),
            "err_info": r[5] or "",
        },
        "info": {
            "err": r[5] or "",
            "data": info_data,
        },
    }
    return {"error": None, "data": detail}


@router.post("/contest/create")
async def contest_create(request: Request, payload: dict = Body(...)):
    await _ensure_contest_schema()
    admin_username = await _require_admin_username(request)

    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    start_time_raw = str(payload.get("start_time", "")).strip()
    end_time_raw = str(payload.get("end_time", "")).strip()
    visible = bool(payload.get("visible", True))
    problem_ids = payload.get("problem_ids")

    if not title or len(title) > 255:
        return {"error": "Invalid title", "data": "Invalid title"}
    if not isinstance(problem_ids, list) or not problem_ids:
        return {"error": "problem_ids is required", "data": "problem_ids is required"}

    normalized_problem_ids: list[str] = []
    for pid in problem_ids:
        v = str(pid).strip()
        if v:
            normalized_problem_ids.append(v)
    normalized_problem_ids = list(dict.fromkeys(normalized_problem_ids))
    if not normalized_problem_ids:
        return {"error": "problem_ids is required", "data": "problem_ids is required"}

    try:
        start_time = datetime.fromisoformat(start_time_raw.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_time_raw.replace("Z", "+00:00"))
    except ValueError:
        return {"error": "Invalid contest time", "data": "Invalid contest time"}

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    if end_time <= start_time:
        return {"error": "end_time must be later than start_time", "data": "end_time must be later than start_time"}

    now = _utc_now()
    status = _contest_status(start_time, end_time, now)

    async with async_session() as db:
        existing_rows = (
            await db.execute(
                text("SELECT _id FROM problem WHERE _id = ANY(:problem_ids)"),
                {"problem_ids": normalized_problem_ids},
            )
        ).fetchall()
        existing_ids = {str(r[0]) for r in existing_rows}
        missing = [pid for pid in normalized_problem_ids if pid not in existing_ids]
        if missing:
            return {"error": "Problem not found", "data": {"missing_problem_ids": missing}}

        contest_row = (
            await db.execute(
                text(
                    "INSERT INTO ai_agent.contests (id,title,description,start_time,end_time,status,visible,created_by,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),:title,:description,:start_time,:end_time,:status,:visible,:created_by,:now,:now) "
                    "RETURNING id"
                ),
                {
                    "title": title,
                    "description": description or None,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": status,
                    "visible": visible,
                    "created_by": admin_username,
                    "now": now,
                },
            )
        ).fetchone()

        contest_id = str(contest_row[0])
        for idx, pid in enumerate(normalized_problem_ids):
            await db.execute(
                text(
                    "INSERT INTO ai_agent.contest_problems (id,contest_id,problem_id,display_order) "
                    "VALUES (gen_random_uuid(),:contest_id,:problem_id,:display_order)"
                ),
                {
                    "contest_id": contest_id,
                    "problem_id": pid,
                    "display_order": idx,
                },
            )
        await db.commit()

    return {"error": None, "data": {"contest_id": contest_id}}


@router.get("/contest/list")
async def contest_list(status: str = Query(default="all")):
    await _ensure_contest_schema()
    status_filter = str(status or "all").strip().lower()
    allowed = {"all", "upcoming", "running", "ended"}
    if status_filter not in allowed:
        status_filter = "all"

    now = _utc_now()
    async with async_session() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id,title,description,start_time,end_time,created_by,created_at,updated_at "
                    "FROM ai_agent.contests ORDER BY start_time DESC"
                )
            )
        ).fetchall()

    results = []
    for r in rows:
        computed_status = _contest_status(r[3], r[4], now)
        if status_filter != "all" and computed_status != status_filter:
            continue
        results.append(
            {
                "id": str(r[0]),
                "title": r[1],
                "description": r[2] or "",
                "start_time": r[3].isoformat(),
                "end_time": r[4].isoformat(),
                "status": computed_status,
                "created_by": r[5],
                "created_at": r[6].isoformat() if r[6] else "",
                "updated_at": r[7].isoformat() if r[7] else "",
            }
        )
    return {"error": None, "data": {"results": results}}


@router.get("/contest/detail")
async def contest_detail(request: Request, contest_id: str = Query(...)):
    await _ensure_contest_schema()
    parsed_contest_id = _parse_uuid(contest_id)
    if not parsed_contest_id:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    username = _current_username(request)
    now = _utc_now()

    async with async_session() as db:
        contest = (
            await db.execute(
                text(
                    "SELECT id,title,description,start_time,end_time,created_by,created_at,updated_at "
                    "FROM ai_agent.contests WHERE id=:contest_id LIMIT 1"
                ),
                {"contest_id": parsed_contest_id},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        problem_rows = (
            await db.execute(
                text(
                    "SELECT cp.problem_id, p.id, p._id, p.title, p.difficulty, p.time_limit, p.memory_limit, cp.display_order "
                    "FROM ai_agent.contest_problems cp "
                    "JOIN problem p ON p._id = cp.problem_id "
                    "WHERE cp.contest_id=:contest_id "
                    "ORDER BY cp.display_order ASC, p.id ASC"
                ),
                {"contest_id": parsed_contest_id},
            )
        ).fetchall()

        joined = False
        if username:
            joined_row = (
                await db.execute(
                    text(
                        "SELECT 1 FROM ai_agent.contest_participants "
                        "WHERE contest_id=:contest_id AND user_id=:user_id LIMIT 1"
                    ),
                    {"contest_id": parsed_contest_id, "user_id": username},
                )
            ).fetchone()
            joined = bool(joined_row)

    result = {
        "id": str(contest[0]),
        "title": contest[1],
        "description": contest[2] or "",
        "start_time": contest[3].isoformat(),
        "end_time": contest[4].isoformat(),
        "status": _contest_status(contest[3], contest[4], now),
        "created_by": contest[5],
        "created_at": contest[6].isoformat() if contest[6] else "",
        "updated_at": contest[7].isoformat() if contest[7] else "",
        "joined": joined,
        "problems": [
            {
                "problem_id": r[0],
                "id": r[1],
                "_id": r[2],
                "title": r[3],
                "difficulty": r[4] or "Low",
                "time_limit": int(r[5] or 1000),
                "memory_limit": int(r[6] or 256),
                "display_order": int(r[7] or 0),
            }
            for r in problem_rows
        ],
    }
    return {"error": None, "data": result}


@router.post("/contest/join")
async def contest_join(request: Request, payload: dict = Body(...)):
    await _ensure_contest_schema()
    username = _current_username(request)
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    parsed_contest_id = _parse_uuid(payload.get("contest_id"))
    if not parsed_contest_id:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    async with async_session() as db:
        contest = (
            await db.execute(
                text("SELECT id FROM ai_agent.contests WHERE id=:contest_id LIMIT 1"),
                {"contest_id": parsed_contest_id},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        try:
            await db.execute(
                text(
                    "INSERT INTO ai_agent.contest_participants (id,contest_id,user_id,joined_at) "
                    "VALUES (gen_random_uuid(),:contest_id,:user_id,:now)"
                ),
                {
                    "contest_id": parsed_contest_id,
                    "user_id": username,
                    "now": _utc_now(),
                },
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()

    return {"error": None, "data": {"contest_id": parsed_contest_id, "joined": True}}


@router.post("/contest/submission")
async def contest_submit_code(request: Request, payload: dict = Body(...)):
    await _ensure_contest_schema()
    username = _current_username(request)
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    parsed_contest_id = _parse_uuid(payload.get("contest_id"))
    problem_id = str(payload.get("problem_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    code = str(payload.get("code", ""))

    if not parsed_contest_id or not problem_id or not language or not code:
        return {"error": "Invalid payload", "data": "Invalid payload"}

    async with async_session() as db:
        contest = (
            await db.execute(
                text(
                    "SELECT id,start_time,end_time FROM ai_agent.contests "
                    "WHERE id=:contest_id LIMIT 1"
                ),
                {"contest_id": parsed_contest_id},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        now = _utc_now()
        status = _contest_status(contest[1], contest[2], now)
        if status != "running":
            return {"error": "Contest is not running", "data": "Contest is not running"}

        joined = (
            await db.execute(
                text(
                    "SELECT 1 FROM ai_agent.contest_participants "
                    "WHERE contest_id=:contest_id AND user_id=:user_id LIMIT 1"
                ),
                {"contest_id": parsed_contest_id, "user_id": username},
            )
        ).fetchone()
        if not joined:
            return {"error": "Please join contest first", "data": "Please join contest first"}

        contest_problem = (
            await db.execute(
                text(
                    "SELECT 1 FROM ai_agent.contest_problems "
                    "WHERE contest_id=:contest_id AND problem_id=:problem_id LIMIT 1"
                ),
                {"contest_id": parsed_contest_id, "problem_id": problem_id},
            )
        ).fetchone()
        if not contest_problem:
            return {"error": "Problem not in contest", "data": "Problem not in contest"}

    lang_map = {
        "C++": "cpp",
        "C": "c",
        "Java": "java",
        "Python3": "python3",
        "cpp": "cpp",
        "c": "c",
        "java": "java",
        "python3": "python3",
    }
    normalized_lang = lang_map.get(language, language)

    sandbox = SandboxClient()
    if not await sandbox.health():
        raise HTTPException(status_code=503, detail="Sandbox unavailable")

    result = await judge_submission(
        code=code,
        language=normalized_lang,
        problem_id=problem_id,
        sandbox=sandbox,
        user_id=username,
    )

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "INSERT INTO ai_agent.submissions (id,problem_id,user_id,language,code,verdict,time_sec,memory_kb,test_case_results,compile_error,contest_id,is_contest,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),:pid,:uid,:lang,:code,:verdict,:time,:mem,CAST(:tcr AS jsonb),:ce,:contest_id,true,:now,:now) RETURNING id"
                ),
                {
                    "pid": problem_id,
                    "uid": username,
                    "lang": normalized_lang,
                    "code": code,
                    "verdict": result.verdict,
                    "time": float(result.total_time_sec or 0),
                    "mem": int(result.max_rss_kb or 0),
                    "tcr": json.dumps(result.test_case_results or [], ensure_ascii=False),
                    "ce": result.compile_error or "",
                    "contest_id": parsed_contest_id,
                    "now": _utc_now(),
                },
            )
        ).fetchone()
        await db.commit()

    return {"error": None, "data": {"submission_id": str(row[0])}}


@router.get("/contest/rank")
async def contest_rank(contest_id: str = Query(...)):
    await _ensure_contest_schema()
    parsed_contest_id = _parse_uuid(contest_id)
    if not parsed_contest_id:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    async with async_session() as db:
        contest = (
            await db.execute(
                text(
                    "SELECT id,start_time,end_time FROM ai_agent.contests "
                    "WHERE id=:contest_id LIMIT 1"
                ),
                {"contest_id": parsed_contest_id},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        participants = (
            await db.execute(
                text(
                    "SELECT user_id, joined_at FROM ai_agent.contest_participants "
                    "WHERE contest_id=:contest_id ORDER BY joined_at ASC"
                ),
                {"contest_id": parsed_contest_id},
            )
        ).fetchall()

        submissions = (
            await db.execute(
                text(
                    "SELECT user_id, problem_id, verdict, created_at "
                    "FROM ai_agent.submissions "
                    "WHERE contest_id=:contest_id AND is_contest=true "
                    "ORDER BY created_at ASC"
                ),
                {"contest_id": parsed_contest_id},
            )
        ).fetchall()

    contest_start_time = contest[1]
    rank_state: dict[str, dict[str, Any]] = {}
    for p in participants:
        rank_state[str(p[0])] = {
            "user_id": str(p[0]),
            "joined_at": p[1],
            "solved_count": 0,
            "penalty_time_ms": 0,
            "problems": {},
        }

    for row in submissions:
        user_id = str(row[0])
        problem_id = str(row[1])
        verdict = str(row[2] or "SE")
        created_at = row[3]

        if user_id not in rank_state:
            rank_state[user_id] = {
                "user_id": user_id,
                "joined_at": contest_start_time,
                "solved_count": 0,
                "penalty_time_ms": 0,
                "problems": {},
            }

        pstate = rank_state[user_id]
        prob_state = pstate["problems"].setdefault(
            problem_id,
            {"solved": False, "wrong_before_ac": 0},
        )

        if prob_state["solved"]:
            continue

        if verdict == "AC":
            elapsed_ms = int((created_at - contest_start_time).total_seconds() * 1000)
            wrong_penalty_ms = int(prob_state["wrong_before_ac"]) * 20 * 60 * 1000
            pstate["solved_count"] += 1
            pstate["penalty_time_ms"] += max(0, elapsed_ms) + wrong_penalty_ms
            prob_state["solved"] = True
        else:
            prob_state["wrong_before_ac"] += 1

    rows = list(rank_state.values())
    rows.sort(
        key=lambda item: (
            -int(item["solved_count"]),
            int(item["penalty_time_ms"]),
            item["joined_at"],
            item["user_id"],
        )
    )

    ranked = []
    for idx, item in enumerate(rows, start=1):
        ranked.append(
            {
                "rank": idx,
                "user_id": item["user_id"],
                "solved_count": int(item["solved_count"]),
                "penalty_time_ms": int(item["penalty_time_ms"]),
                "joined_at": item["joined_at"].isoformat() if item.get("joined_at") else "",
            }
        )

    return {"error": None, "data": {"results": ranked}}
