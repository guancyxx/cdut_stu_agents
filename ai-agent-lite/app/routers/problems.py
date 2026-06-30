"""Problem routes: list and detail, compatible with QDUOJ frontend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request
from sqlalchemy import text

from app.database import async_session
from app.utils.auth_helpers import current_username
from app.utils.oj_helpers import parse_json

router = APIRouter(prefix="/api", tags=["problems"])


@router.get("/problem/")
async def list_or_get_problem(
    request: Request,
    problem_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    limit: int = Query(default=21, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    if not current_username(request):
        return {"error": "Please login first", "data": "Please login first"}
    async with async_session() as db:
        # ── single-problem detail ──
        if problem_id:
            row = (
                await db.execute(
                    text(
                        "SELECT id,_id,title,description,input_description,"
                        "output_description,samples,hint,source,difficulty,"
                        "time_limit,memory_limit,languages,template "
                        "FROM problem WHERE _id=:pid OR CAST(id AS TEXT)=:pid LIMIT 1",
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
                    "samples": parse_json(row[6], []),
                    "hint": row[7] or "",
                    "source": row[8] or "",
                    "difficulty": row[9] or "Low",
                    "time_limit": int(row[10] or 1000),
                    "memory_limit": int(row[11] or 256),
                    "languages": parse_json(
                        row[12], ["C", "C++", "Java", "Python3"],
                    ),
                    "template": parse_json(row[13], {}),
                },
            }

        # ── list with filters ──
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
            await db.execute(
                text(f"SELECT COUNT(*) FROM problem WHERE {where_sql}"), params,
            )
        ).scalar_one()

        rows = (
            await db.execute(
                text(
                    f"SELECT id,_id,title,difficulty,time_limit,memory_limit "
                    f"FROM problem WHERE {where_sql} "
                    f"ORDER BY id DESC LIMIT :limit OFFSET :offset",
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
