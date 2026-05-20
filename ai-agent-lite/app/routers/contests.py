"""Contest routes: CRUD, join, submit, rank — QDUOJ-compatible API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.database import async_session
from app.services.judge_service import SandboxClient, judge_submission
from app.utils.auth_helpers import current_username, require_admin_username
from app.utils.oj_helpers import (
    parse_uuid, utc_now, contest_status, normalize_language,
)

router = APIRouter(prefix="/api", tags=["contests"])


# ── schema bootstrap ──────────────────────────────────────────────────

async def ensure_contest_schema() -> None:
    """Create contest tables and schema if they don't exist."""
    async with async_session() as db:
        await db.execute(text("CREATE SCHEMA IF NOT EXISTS ai_agent"))
        await db.execute(text("ALTER TABLE ai_agent.local_users ADD COLUMN IF NOT EXISTS signature varchar(280)"))
        await db.execute(text("""
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
        """))
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_agent.contest_problems (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                contest_id uuid NOT NULL
                    REFERENCES ai_agent.contests(id) ON DELETE CASCADE,
                problem_id varchar(64) NOT NULL,
                display_order integer NOT NULL DEFAULT 0,
                UNIQUE (contest_id, problem_id)
            )
        """))
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_agent.contest_participants (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                contest_id uuid NOT NULL
                    REFERENCES ai_agent.contests(id) ON DELETE CASCADE,
                user_id varchar(64) NOT NULL,
                joined_at timestamptz NOT NULL,
                UNIQUE (contest_id, user_id)
            )
        """))
        await db.execute(text(
            "ALTER TABLE ai_agent.submissions "
            "ADD COLUMN IF NOT EXISTS contest_id uuid NULL",
        ))
        await db.execute(text(
            "ALTER TABLE ai_agent.submissions "
            "ADD COLUMN IF NOT EXISTS is_contest boolean NOT NULL DEFAULT false",
        ))
        await db.execute(text(
            "ALTER TABLE ai_agent.contests "
            "ADD COLUMN IF NOT EXISTS visible boolean NOT NULL DEFAULT true",
        ))
        await db.commit()


# ── contest validation helper (reused by submissions.py) ──────────────

async def validate_contest_submit(
    problem_id: str, contest_id_raw: Any, username: str,
) -> str | dict:
    """Validate contest submit preconditions. Returns contest_id or error dict."""
    contest_id = parse_uuid(str(contest_id_raw))
    if not contest_id:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    async with async_session() as db:
        contest = (
            await db.execute(
                text(
                    "SELECT id,start_time,end_time "
                    "FROM ai_agent.contests WHERE id=:cid LIMIT 1",
                ),
                {"cid": contest_id},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        now = utc_now()
        if contest_status(contest[1], contest[2], now) != "running":
            return {
                "error": "Contest is not running",
                "data": "Contest is not running",
            }

        joined = (
            await db.execute(
                text(
                    "SELECT 1 FROM ai_agent.contest_participants "
                    "WHERE contest_id=:cid AND user_id=:uid LIMIT 1",
                ),
                {"cid": contest_id, "uid": username},
            )
        ).fetchone()
        if not joined:
            return {
                "error": "Please join contest first",
                "data": "Please join contest first",
            }

        cp = (
            await db.execute(
                text(
                    "SELECT 1 FROM ai_agent.contest_problems "
                    "WHERE contest_id=:cid AND problem_id=:pid LIMIT 1",
                ),
                {"cid": contest_id, "pid": problem_id},
            )
        ).fetchone()
        if not cp:
            return {
                "error": "Problem not in contest",
                "data": "Problem not in contest",
            }

    return contest_id


# ── create ─────────────────────────────────────────────────────────────

@router.post("/contest/create")
async def contest_create(request: Request, payload: dict = Body(...)):
    await ensure_contest_schema()
    admin_username = await require_admin_username(request)

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

    normalized_pids: list[str] = list(dict.fromkeys(
        str(pid).strip() for pid in problem_ids if str(pid).strip()
    ))
    if not normalized_pids:
        return {"error": "problem_ids is required", "data": "problem_ids is required"}

    try:
        start_time = datetime.fromisoformat(
            start_time_raw.replace("Z", "+00:00"),
        )
        end_time = datetime.fromisoformat(
            end_time_raw.replace("Z", "+00:00"),
        )
    except ValueError:
        return {"error": "Invalid contest time", "data": "Invalid contest time"}

    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    if end_time <= start_time:
        return {
            "error": "end_time must be later than start_time",
            "data": "end_time must be later than start_time",
        }

    now = utc_now()
    status = contest_status(start_time, end_time, now)

    async with async_session() as db:
        existing_rows = (
            await db.execute(
                text("SELECT _id FROM problem WHERE _id = ANY(:pids)"),
                {"pids": normalized_pids},
            )
        ).fetchall()
        existing_ids = {str(r[0]) for r in existing_rows}
        missing = [pid for pid in normalized_pids if pid not in existing_ids]
        if missing:
            return {
                "error": "Problem not found",
                "data": {"missing_problem_ids": missing},
            }

        contest_row = (
            await db.execute(
                text(
                    "INSERT INTO ai_agent.contests "
                    "(id,title,description,start_time,end_time,status,visible,"
                    " created_by,created_at,updated_at) "
                    "VALUES (gen_random_uuid(),:t,:d,:st,:et,:s,:v,:cb,:n,:n) "
                    "RETURNING id",
                ),
                {
                    "t": title, "d": description or None,
                    "st": start_time, "et": end_time,
                    "s": status, "v": visible,
                    "cb": admin_username, "n": now,
                },
            )
        ).fetchone()

        contest_id = str(contest_row[0])
        for idx, pid in enumerate(normalized_pids):
            await db.execute(
                text(
                    "INSERT INTO ai_agent.contest_problems "
                    "(id,contest_id,problem_id,display_order) "
                    "VALUES (gen_random_uuid(),:cid,:pid,:ord)",
                ),
                {"cid": contest_id, "pid": pid, "ord": idx},
            )
        await db.commit()

    return {"error": None, "data": {"contest_id": contest_id}}


# ── list ───────────────────────────────────────────────────────────────

@router.get("/contest/list")
async def contest_list(status: str = Query(default="all")):
    await ensure_contest_schema()
    status_filter = str(status or "all").strip().lower()
    if status_filter not in {"all", "upcoming", "running", "ended"}:
        status_filter = "all"

    now = utc_now()
    async with async_session() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT id,title,description,start_time,end_time,"
                    "created_by,created_at,updated_at "
                    "FROM ai_agent.contests ORDER BY start_time DESC",
                ),
            )
        ).fetchall()

    results = []
    for r in rows:
        cs = contest_status(r[3], r[4], now)
        if status_filter != "all" and cs != status_filter:
            continue
        results.append({
            "id": str(r[0]), "title": r[1],
            "description": r[2] or "",
            "start_time": r[3].isoformat(),
            "end_time": r[4].isoformat(),
            "status": cs,
            "created_by": r[5],
            "created_at": r[6].isoformat() if r[6] else "",
            "updated_at": r[7].isoformat() if r[7] else "",
        })
    return {"error": None, "data": {"results": results}}


# ── detail ─────────────────────────────────────────────────────────────

@router.get("/contest/detail")
async def contest_detail(request: Request, contest_id: str = Query(...)):
    await ensure_contest_schema()
    cid = parse_uuid(contest_id)
    if not cid:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    username = current_username(request)
    now = utc_now()

    async with async_session() as db:
        contest = (
            await db.execute(
                text(
                    "SELECT id,title,description,start_time,end_time,"
                    "created_by,created_at,updated_at "
                    "FROM ai_agent.contests WHERE id=:cid LIMIT 1",
                ),
                {"cid": cid},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        problem_rows = (
            await db.execute(
                text(
                    "SELECT cp.problem_id, p.id, p._id, p.title, p.difficulty, "
                    "p.time_limit, p.memory_limit, cp.display_order "
                    "FROM ai_agent.contest_problems cp "
                    "JOIN problem p ON p._id = cp.problem_id "
                    "WHERE cp.contest_id=:cid "
                    "ORDER BY cp.display_order ASC, p.id ASC",
                ),
                {"cid": cid},
            )
        ).fetchall()

        joined = False
        if username:
            jr = (
                await db.execute(
                    text(
                        "SELECT 1 FROM ai_agent.contest_participants "
                        "WHERE contest_id=:cid AND user_id=:uid LIMIT 1",
                    ),
                    {"cid": cid, "uid": username},
                )
            ).fetchone()
            joined = bool(jr)

    return {
        "error": None,
        "data": {
            "id": str(contest[0]),
            "title": contest[1],
            "description": contest[2] or "",
            "start_time": contest[3].isoformat(),
            "end_time": contest[4].isoformat(),
            "status": contest_status(contest[3], contest[4], now),
            "created_by": contest[5],
            "created_at": contest[6].isoformat() if contest[6] else "",
            "updated_at": contest[7].isoformat() if contest[7] else "",
            "joined": joined,
            "problems": [
                {
                    "problem_id": r[0], "id": r[1], "_id": r[2],
                    "title": r[3], "difficulty": r[4] or "Low",
                    "time_limit": int(r[5] or 1000),
                    "memory_limit": int(r[6] or 256),
                    "display_order": int(r[7] or 0),
                }
                for r in problem_rows
            ],
        },
    }


# ── join ───────────────────────────────────────────────────────────────

@router.post("/contest/join")
async def contest_join(request: Request, payload: dict = Body(...)):
    await ensure_contest_schema()
    username = current_username(request)
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    cid_raw = payload.get("contest_id")
    if not cid_raw:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}
    cid = parse_uuid(str(cid_raw))
    if not cid:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    async with async_session() as db:
        contest = (
            await db.execute(
                text("SELECT id FROM ai_agent.contests WHERE id=:cid LIMIT 1"),
                {"cid": cid},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        try:
            await db.execute(
                text(
                    "INSERT INTO ai_agent.contest_participants "
                    "(id,contest_id,user_id,joined_at) "
                    "VALUES (gen_random_uuid(),:cid,:uid,:n)",
                ),
                {"cid": cid, "uid": username, "n": utc_now()},
            )
            await db.commit()
        except IntegrityError:
            await db.rollback()

    return {"error": None, "data": {"contest_id": cid, "joined": True}}


# ── contest submit ─────────────────────────────────────────────────────

@router.post("/contest/submission")
async def contest_submit_code(request: Request, payload: dict = Body(...)):
    await ensure_contest_schema()
    username = current_username(request)
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    problem_id = str(payload.get("problem_id", "")).strip()
    language = str(payload.get("language", "")).strip()
    code = str(payload.get("code", ""))
    contest_id_raw = payload.get("contest_id")

    if not contest_id_raw or not problem_id or not language or not code:
        return {"error": "Invalid payload", "data": "Invalid payload"}

    validation = await validate_contest_submit(problem_id, contest_id_raw, username)
    if isinstance(validation, dict):
        return validation  # error dict
    contest_id = validation

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
                    ":time,:mem,CAST(:tcr AS jsonb),:ce,:cid,true,:n,:n) "
                    "RETURNING id",
                ),
                {
                    "pid": problem_id, "uid": username,
                    "lang": normalized_lang, "code": code,
                    "verdict": result.verdict,
                    "time": float(result.total_time_sec or 0),
                    "mem": int(result.max_rss_kb or 0),
                    "tcr": json.dumps(result.test_case_results or [], ensure_ascii=False),
                    "ce": result.compile_error or "",
                    "cid": contest_id, "n": now,
                },
            )
        ).fetchone()
        await db.commit()

    return {"error": None, "data": {"submission_id": str(row[0])}}


# ── rank ───────────────────────────────────────────────────────────────

@router.get("/contest/rank")
async def contest_rank(contest_id: str = Query(...)):
    await ensure_contest_schema()
    cid = parse_uuid(contest_id)
    if not cid:
        return {"error": "Invalid contest id", "data": "Invalid contest id"}

    async with async_session() as db:
        contest = (
            await db.execute(
                text(
                    "SELECT id,start_time,end_time "
                    "FROM ai_agent.contests WHERE id=:cid LIMIT 1",
                ),
                {"cid": cid},
            )
        ).fetchone()
        if not contest:
            return {"error": "Contest not found", "data": "Contest not found"}

        participants = (
            await db.execute(
                text(
                    "SELECT p.user_id, p.joined_at, COALESCE(u.signature,'') AS signature "
                    "FROM ai_agent.contest_participants p "
                    "LEFT JOIN ai_agent.local_users u ON u.username = p.user_id "
                    "WHERE p.contest_id=:cid ORDER BY p.joined_at ASC",
                ),
                {"cid": cid},
            )
        ).fetchall()

        submissions = (
            await db.execute(
                text(
                    "SELECT user_id, problem_id, verdict, created_at "
                    "FROM ai_agent.submissions "
                    "WHERE contest_id=:cid AND is_contest=true "
                    "ORDER BY created_at ASC",
                ),
                {"cid": cid},
            )
        ).fetchall()

    contest_start = contest[1]
    rank_state: dict[str, dict[str, Any]] = {}
    for p in participants:
        rank_state[str(p[0])] = {
            "user_id": str(p[0]), "joined_at": p[1], "signature": str(p[2] or ''),
            "solved_count": 0, "penalty_time_ms": 0, "problems": {},
        }

    for row in submissions:
        uid = str(row[0])
        pid = str(row[1])
        verdict = str(row[2] or "SE")
        created_at = row[3]

        if uid not in rank_state:
            rank_state[uid] = {
                "user_id": uid, "joined_at": contest_start, "signature": '',
                "solved_count": 0, "penalty_time_ms": 0, "problems": {},
            }

        ps = rank_state[uid]
        prob = ps["problems"].setdefault(
            pid, {"solved": False, "wrong_before_ac": 0},
        )

        if prob["solved"]:
            continue

        if verdict == "AC":
            elapsed = int((created_at - contest_start).total_seconds() * 1000)
            penalty = int(prob["wrong_before_ac"]) * 20 * 60 * 1000
            ps["solved_count"] += 1
            ps["penalty_time_ms"] += max(0, elapsed) + penalty
            prob["solved"] = True
        else:
            prob["wrong_before_ac"] += 1

    rows = list(rank_state.values())
    rows.sort(key=lambda item: (
        -int(item["solved_count"]),
        int(item["penalty_time_ms"]),
        item["joined_at"],
        item["user_id"],
    ))

    ranked = [
        {
            "rank": idx, "user_id": item["user_id"], "signature": str(item.get("signature") or ''),
            "solved_count": int(item["solved_count"]),
            "penalty_time_ms": int(item["penalty_time_ms"]),
            "joined_at": item["joined_at"].isoformat()
            if item.get("joined_at") else "",
        }
        for idx, item in enumerate(rows, start=1)
    ]

    return {"error": None, "data": {"results": ranked}}
