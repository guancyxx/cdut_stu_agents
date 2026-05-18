"""Admin account management endpoints for local_users table."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.database import async_session
from app.utils.auth_helpers import EMAIL_RE, USERNAME_RE, hash_password, require_admin_username

router = APIRouter(prefix="/admin/accounts", tags=["admin-accounts"])


class AccountCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    email: str = Field(default="", max_length=120)
    student_number: str = Field(default="", max_length=64)
    admin_type: int = Field(default=0, ge=0, le=2)


class AccountUpdateRequest(BaseModel):
    email: str = Field(default="", max_length=120)
    student_number: str = Field(default="", max_length=64)
    admin_type: int = Field(default=0, ge=0, le=2)
    password: str = Field(default="", max_length=128)


def _normalize_email(email: str) -> str | None:
    val = str(email or "").strip()
    if not val:
        return None
    if not EMAIL_RE.match(val):
        raise HTTPException(status_code=400, detail="Invalid email")
    return val


def _validate_username(username: str) -> str:
    val = str(username or "").strip()
    if not USERNAME_RE.match(val):
        raise HTTPException(status_code=400, detail="Invalid username")
    return val


@router.get("")
async def list_accounts(request: Request):
    await require_admin_username(request)

    async with async_session() as db:
        rows = (
            await db.execute(
                text(
                    "SELECT username, COALESCE(email,''), COALESCE(student_number,''), "
                    "COALESCE(admin_type,0), created_at, updated_at "
                    "FROM ai_agent.local_users ORDER BY admin_type DESC, username ASC"
                )
            )
        ).fetchall()

    return {
        "error": None,
        "data": {
            "results": [
                {
                    "username": r[0],
                    "email": r[1],
                    "student_number": r[2],
                    "admin_type": int(r[3] or 0),
                    "created_at": r[4].isoformat() if r[4] else "",
                    "updated_at": r[5].isoformat() if r[5] else "",
                }
                for r in rows
            ]
        },
    }


@router.post("")
async def create_account(request: Request, payload: AccountCreateRequest = Body(...)):
    operator = await require_admin_username(request)

    username = _validate_username(payload.username)
    email = _normalize_email(payload.email)
    student_number = str(payload.student_number or "").strip() or None
    admin_type = int(payload.admin_type)

    async with async_session() as db:
        op_row = (
            await db.execute(
                text("SELECT COALESCE(admin_type,0) FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": operator},
            )
        ).fetchone()
        operator_admin_type = int(op_row[0] or 0) if op_row else 0
        if operator_admin_type < 2 and admin_type == 2:
            raise HTTPException(status_code=403, detail="Only super admin can create super admin")

        exists = (
            await db.execute(
                text("SELECT 1 FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": username},
            )
        ).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="Username already exists")

        now = datetime.now(timezone.utc)
        await db.execute(
            text(
                "INSERT INTO ai_agent.local_users "
                "(username, password_hash, email, student_number, admin_type, created_at, updated_at) "
                "VALUES (:u, :p, :e, :s, :a, :now, :now)"
            ),
            {
                "u": username,
                "p": hash_password(payload.password),
                "e": email,
                "s": student_number,
                "a": admin_type,
                "now": now,
            },
        )
        await db.commit()

    return {"error": None, "data": {"username": username, "message": "created"}}


@router.put("/{username}")
async def update_account(username: str, request: Request, payload: AccountUpdateRequest = Body(...)):
    operator = await require_admin_username(request)
    target_username = _validate_username(username)

    email = _normalize_email(payload.email)
    student_number = str(payload.student_number or "").strip() or None
    admin_type = int(payload.admin_type)
    new_password = str(payload.password or "")

    async with async_session() as db:
        op_row = (
            await db.execute(
                text("SELECT COALESCE(admin_type,0) FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": operator},
            )
        ).fetchone()
        operator_admin_type = int(op_row[0] or 0) if op_row else 0
        if operator_admin_type < 2 and admin_type == 2:
            raise HTTPException(status_code=403, detail="Only super admin can assign super admin")

        target_row = (
            await db.execute(
                text("SELECT username FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": target_username},
            )
        ).fetchone()
        if not target_row:
            raise HTTPException(status_code=404, detail="Account not found")

        target_admin_type_row = (
            await db.execute(
                text("SELECT COALESCE(admin_type,0) FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": target_username},
            )
        ).fetchone()
        target_admin_type = int(target_admin_type_row[0] or 0) if target_admin_type_row else 0
        if operator_admin_type < 2 and target_admin_type == 2:
            raise HTTPException(status_code=403, detail="Only super admin can modify super admin")

        await db.execute(
            text(
                "UPDATE ai_agent.local_users SET "
                "email=:e, student_number=:s, admin_type=:a, updated_at=:now "
                "WHERE username=:u"
            ),
            {
                "u": target_username,
                "e": email,
                "s": student_number,
                "a": admin_type,
                "now": datetime.now(timezone.utc),
            },
        )

        if new_password:
            if len(new_password) < 6:
                raise HTTPException(status_code=400, detail="Password too short")
            await db.execute(
                text(
                    "UPDATE ai_agent.local_users SET password_hash=:p, updated_at=:now "
                    "WHERE username=:u"
                ),
                {
                    "u": target_username,
                    "p": hash_password(new_password),
                    "now": datetime.now(timezone.utc),
                },
            )

        await db.commit()

    return {"error": None, "data": {"username": target_username, "message": "updated"}}


@router.delete("/{username}")
async def delete_account(username: str, request: Request):
    operator = await require_admin_username(request)
    target_username = _validate_username(username)

    if operator == target_username:
        raise HTTPException(status_code=400, detail="Cannot delete current login account")

    async with async_session() as db:
        target_row = (
            await db.execute(
                text("SELECT COALESCE(admin_type,0) FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": target_username},
            )
        ).fetchone()
        if not target_row:
            raise HTTPException(status_code=404, detail="Account not found")

        op_row = (
            await db.execute(
                text("SELECT COALESCE(admin_type,0) FROM ai_agent.local_users WHERE username=:u LIMIT 1"),
                {"u": operator},
            )
        ).fetchone()
        operator_admin_type = int(op_row[0] or 0) if op_row else 0

        # Keep at least one admin account.
        admin_count_row = (
            await db.execute(
                text("SELECT COUNT(*) FROM ai_agent.local_users WHERE COALESCE(admin_type,0) >= 1")
            )
        ).fetchone()
        admin_count = int(admin_count_row[0] or 0)
        target_admin = int(target_row[0] or 0)

        if operator_admin_type < 2 and target_admin == 2:
            raise HTTPException(status_code=403, detail="Only super admin can delete super admin")
        if target_admin >= 1 and admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete last admin account")

        await db.execute(
            text("DELETE FROM ai_agent.local_users WHERE username=:u"),
            {"u": target_username},
        )
        await db.commit()

    return {"error": None, "data": {"username": target_username, "message": "deleted"}}
