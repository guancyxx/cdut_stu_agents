"""Submission routes: list, submit, detail — QDUOJ-compatible API."""

from __future__ import annotations

import json

from fastapi import APIRouter, Body, HTTPException, Query, Request
from sqlalchemy import text

from app.database import async_session
from app.services.judge_service import SandboxClient, judge_submission
from app.utils.auth_helpers import current_username
from app.utils.oj_helpers import (
    status_code_from_verdict, parse_json, normalize_language, utc_now,
)

router = APIRouter(prefix="/api", tags=["submissions"])


# ── list ───────────────────────────────────────────────────────────────

@router.get("/submissions")
async def list_submissions(
    request: Request,
    problem_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
):
    username = current_username(request) or "anonymous"
    offset = (page - 1) * limit
    resolved_pid = problem_id

    async with async_session() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id, problem_id, user_id, verdict, time_sec, "
                    "memory_kb, compile_error, test_case_results, created_at "
                    "FROM ai_agent.submissions "
                    "WHERE user_id=:u "
                    + ("AND problem_id=:pid " if resolved_pid else "")
                    + "ORDER BY created_at DESC LIMIT :limit OFFSET :offset",
                ),
                {"u": username, "pid": resolved_pid, "limit": limit, "offset": offset}
                if resolved_pid
                else {"u": username, "limit": limit, "offset": offset},
            )
        ).fetchall()

    results = []
    for r in rows:
        verdict = str(r[3] or "SE")
        code = status_code_from_verdict(verdict)
        tc = parse_json(r[7], [])
        info_data = []
        for case in tc if isinstance(tc, list) else []:
            info_data.append({
                "test_case": int(case.get("case_index", 0)),
                "result": status_code_from_verdict(
                    str(case.get("verdict", "SE")),
                ),
                "cpu_time": int(float(case.get("time_sec", 0)) * 1000),
                "memory": int(case.get("max_rss_kb", 0) or 0) * 1024,
                "score": 0,
                "output": case.get("stdout", ""),
            })

        results.append({
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
        })

    return {"error": None, "data": {"results": results}}


# ── submit ─────────────────────────────────────────────────────────────

@router.post("/submission")
async def submit_code(request: Request, payload: dict = Body(...)):
    # late import to avoid circular dependency with contests
    from app.routers.contests import ensure_contest_schema, validate_contest_submit

    await ensure_contest_schema()

    username = current_username(request) or "anonymous"
    problem_id = str(payload.get("problem_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    code = str(payload.get("code", ""))
    contest_id_raw = payload.get("contest_id")

    if not problem_id or not language or not code:
        return {"error": "Invalid payload", "data": "Invalid payload"}

    parsed_contest_id = None
    is_contest = False
    if contest_id_raw:
        result = await validate_contest_submit(
            problem_id, contest_id_raw, username,
        )
        if isinstance(result, dict):
            return result  # error dict returned
        parsed_contest_id, is_contest = result, True

    normalized_lang = normalize_language(language)

    sandbox = SandboxClient()
    if not await sandbox.health():
        raise HTTPException(status_code=503, detail="Sandbox unavailable")

    result = await judge_submission(
        code=code, language=normalized_lang, problem_id=problem_id,
        sandbox=sandbox, user_id=username,
    )

    async with async_session() as db:
        now = utc_now()
        row = (
            await db.execute(
                text(
                    "INSERT INTO ai_agent.submissions "
                    "(id,problem_id,user_id,language,code,verdict,time_sec,"
                    " memory_kb,test_case_results,compile_error,contest_id,"
                    " is_contest,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),:pid,:uid,:lang,:code,:verdict,"
                    ":time,:mem,CAST(:tcr AS jsonb),:ce,:contest_id,"
                    ":is_contest,:now,:now) RETURNING id",
                ),
                {
                    "pid": problem_id, "uid": username, "lang": normalized_lang,
                    "code": code, "verdict": result.verdict,
                    "time": float(result.total_time_sec or 0),
                    "mem": int(result.max_rss_kb or 0),
                    "tcr": json.dumps(result.test_case_results or [], ensure_ascii=False),
                    "ce": result.compile_error or "",
                    "contest_id": parsed_contest_id,
                    "is_contest": is_contest, "now": now,
                },
            )
        ).fetchone()
        await db.commit()
    submission_id = str(row[0])

    return {"error": None, "data": {"submission_id": submission_id}}


# ── detail ─────────────────────────────────────────────────────────────

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
                    "SELECT id, problem_id, verdict, time_sec, memory_kb, "
                    "compile_error, test_case_results "
                    "FROM ai_agent.submissions WHERE CAST(id AS TEXT)=:sid LIMIT 1",
                ),
                {"sid": submission_id},
            )
        ).fetchone()

    if not r:
        return {"error": "Submission not found", "data": "Submission not found"}

    verdict = str(r[2] or "SE")
    tcr = parse_json(r[6], [])
    info_data = []
    for case in tcr if isinstance(tcr, list) else []:
        info_data.append({
            "test_case": int(case.get("case_index", 0)),
            "result": status_code_from_verdict(
                str(case.get("verdict", "SE")),
            ),
            "cpu_time": int(float(case.get("time_sec", 0)) * 1000),
            "memory": int(case.get("max_rss_kb", 0) or 0) * 1024,
            "score": 0,
            "output": case.get("stdout", ""),
        })

    return {
        "error": None,
        "data": {
            "id": str(r[0]),
            "problem": r[1],
            "result": status_code_from_verdict(verdict),
            "statistic_info": {
                "score": 100 if verdict == "AC" else 0,
                "time_cost": int(float(r[3] or 0) * 1000),
                "memory_cost": int(r[4] or 0),
                "err_info": r[5] or "",
            },
            "info": {"err": r[5] or "", "data": info_data},
        },
    }
