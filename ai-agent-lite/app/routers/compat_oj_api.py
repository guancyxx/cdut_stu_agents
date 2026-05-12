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
    # QDUOJ-compatible status codes used by frontend map
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


@router.get("/captcha")
async def captcha(response: Response):
    # Frontend only checks non-empty data; no real captcha required for local compat.
    response.set_cookie("csrftoken", "lite-csrf-token", httponly=False, samesite="lax")
    return {"error": None, "data": "data:image/svg+xml;base64,PHN2Zy8+"}


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
                    "SELECT username, COALESCE(email,''), COALESCE(admin_type,0), COALESCE(password_hash,'') "
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
            "admin_type": int(row[2] or 0),
            "admin_type_name": "Super Admin" if int(row[2] or 0) == 2 else ("Admin" if int(row[2] or 0) == 1 else "Regular User"),
        },
    }


@router.post("/register")
async def register(response: Response, payload: dict = Body(...)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    email = str(payload.get("email", "")).strip()

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
                "INSERT INTO ai_agent.local_users (username, password_hash, email, admin_type, created_at, updated_at) "
                "VALUES (:u, :p, :e, 0, :now, :now)"
            ),
            {
                "u": username,
                "p": _hash_password(password),
                "e": email or None,
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
                        "SELECT id,_id,title,description,input_description,output_description,samples,hint,source,difficulty,time_limit,memory_limit,languages "
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
    username = _current_username(request) or "anonymous"
    problem_id = str(payload.get("problem_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    code = str(payload.get("code", ""))

    if not problem_id or not language or not code:
        return {"error": "Invalid payload", "data": "Invalid payload"}

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
                    "INSERT INTO ai_agent.submissions (id,problem_id,user_id,language,code,verdict,time_sec,memory_kb,test_case_results,compile_error,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),:pid,:uid,:lang,:code,:verdict,:time,:mem,CAST(:tcr AS jsonb),:ce,:now,:now) RETURNING id"
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
                    "now": datetime.now(timezone.utc),
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
