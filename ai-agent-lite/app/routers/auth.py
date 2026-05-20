"""Authentication routes: login, register, logout, profile, captcha.

Compatible with the legacy QDUOJ frontend API contract.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Request, Response
from sqlalchemy import text

from app.database import async_session
from app.utils.auth_helpers import (
    USERNAME_RE, EMAIL_RE,
    hash_password, verify_password, captcha_svg_data_url, current_username,
)

router = APIRouter(prefix="/api", tags=["auth"])


# ── captcha ────────────────────────────────────────────────────────────

@router.get("/captcha")
async def captcha(response: Response):
    response.set_cookie(
        "csrftoken", "lite-csrf-token", httponly=False, samesite="lax",
    )
    return {"error": None, "data": captcha_svg_data_url()}


# ── profile ────────────────────────────────────────────────────────────

@router.get("/profile")
async def profile(request: Request, response: Response):
    username = current_username(request)
    response.set_cookie(
        "csrftoken", "lite-csrf-token", httponly=False, samesite="lax",
    )
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    async with async_session() as db:
        await db.execute(
            text("ALTER TABLE ai_agent.local_users ADD COLUMN IF NOT EXISTS signature varchar(280)"),
        )
        row = (
            await db.execute(
                text(
                    "SELECT username, COALESCE(email,''), COALESCE(student_number,''), "
                    "COALESCE(admin_type,0), COALESCE(password_hash,''), COALESCE(signature,'') "
                    "FROM ai_agent.local_users WHERE username=:u LIMIT 1",
                ),
                {"u": username},
            )
        ).fetchone()

    if not row:
        return {"error": "Please login first", "data": "Please login first"}

    admin_type = int(row[3] or 0)
    if admin_type == 2:
        admin_name = "Super Admin"
    elif admin_type == 1:
        admin_name = "Admin"
    else:
        admin_name = "Regular User"

    return {
        "error": None,
        "data": {
            "username": row[0],
            "profile_name": row[0],
            "email": row[1],
            "student_number": row[2],
            "admin_type": admin_type,
            "admin_type_name": admin_name,
            "signature": row[5] if len(row) > 5 else '',
        },
    }


@router.put("/profile")
async def update_profile(request: Request, payload: dict = Body(...)):
    username = current_username(request)
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    email = str(payload.get("email", "")).strip()
    student_number = str(payload.get("student_number", "")).strip()
    signature = str(payload.get("signature", "")).strip()

    if email and not EMAIL_RE.match(email):
        return {"error": "Invalid email", "data": "Invalid email"}
    if len(signature) > 280:
        return {"error": "Signature too long", "data": "Signature too long"}

    async with async_session() as db:
        await db.execute(
            text("ALTER TABLE ai_agent.local_users ADD COLUMN IF NOT EXISTS signature varchar(280)"),
        )
        await db.execute(
            text(
                "UPDATE ai_agent.local_users "
                "SET email=:e, student_number=:s, signature=:sig, updated_at=:now "
                "WHERE username=:u"
            ),
            {
                "e": email or None,
                "s": student_number or None,
                "sig": signature,
                "u": username,
                "now": datetime.now(timezone.utc),
            },
        )
        row = (
            await db.execute(
                text(
                    "SELECT username, COALESCE(email,''), COALESCE(student_number,''), COALESCE(admin_type,0), COALESCE(signature,'') "
                    "FROM ai_agent.local_users WHERE username=:u LIMIT 1"
                ),
                {"u": username},
            )
        ).fetchone()
        await db.commit()

    if not row:
        return {"error": "User not found", "data": "User not found"}

    admin_type = int(row[3] or 0)
    if admin_type == 2:
        admin_name = "Super Admin"
    elif admin_type == 1:
        admin_name = "Admin"
    else:
        admin_name = "Regular User"

    return {
        "error": None,
        "data": {
            "username": row[0],
            "profile_name": row[0],
            "email": row[1],
            "student_number": row[2],
            "admin_type": admin_type,
            "admin_type_name": admin_name,
            "signature": row[4],
        },
    }


@router.put("/profile/password")
async def update_profile_password(request: Request, payload: dict = Body(...)):
    username = current_username(request)
    if not username:
        return {"error": "Please login first", "data": "Please login first"}

    old_password = str(payload.get("old_password", ""))
    new_password = str(payload.get("new_password", ""))

    if not old_password or not new_password or len(new_password) < 6:
        return {"error": "Invalid password", "data": "Invalid password"}

    if old_password == new_password:
        return {
            "error": "New password must be different",
            "data": "New password must be different",
        }

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "SELECT password_hash, COALESCE(is_disabled,false) "
                    "FROM ai_agent.local_users WHERE username=:u LIMIT 1"
                ),
                {"u": username},
            )
        ).fetchone()

        if not row:
            return {"error": "User not found", "data": "User not found"}
        if row[1]:
            return {"error": "Account is disabled", "data": "Account is disabled"}
        if not verify_password(old_password, str(row[0] or "")):
            return {"error": "Invalid old password", "data": "Invalid old password"}

        await db.execute(
            text(
                "UPDATE ai_agent.local_users SET password_hash=:p, updated_at=:now "
                "WHERE username=:u"
            ),
            {
                "p": hash_password(new_password),
                "u": username,
                "now": datetime.now(timezone.utc),
            },
        )
        await db.commit()

    return {"error": None, "data": "ok"}


# ── register ───────────────────────────────────────────────────────────

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
            return {
                "error": "Username already exists",
                "data": "Username already exists",
            }

        now = datetime.now(timezone.utc)
        await db.execute(
            text(
                "INSERT INTO ai_agent.local_users "
                "(username, password_hash, email, student_number, admin_type, "
                " created_at, updated_at) "
                "VALUES (:u, :p, :e, :s, 0, :now, :now)",
            ),
            {
                "u": username,
                "p": hash_password(password),
                "e": email or None,
                "s": student_number or None,
                "now": now,
            },
        )
        await db.commit()

    response.set_cookie("lite_user", username, httponly=True, samesite="lax")
    response.set_cookie(
        "csrftoken", "lite-csrf-token", httponly=False, samesite="lax",
    )
    return {"error": None, "data": {"username": username}}


# ── login ──────────────────────────────────────────────────────────────

@router.post("/login")
async def login(response: Response, payload: dict = Body(...)):
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "SELECT username, password_hash, COALESCE(is_disabled,false) "
                    "FROM ai_agent.local_users WHERE username=:u LIMIT 1",
                ),
                {"u": username},
            )
        ).fetchone()

    if not row or not verify_password(password, str(row[1] or "")):
        return {
            "error": "Invalid username or password",
            "data": "Invalid username or password",
        }
    if row[2]:
        return {
            "error": "Account is disabled",
            "data": "Account is disabled",
        }

    response.set_cookie("lite_user", username, httponly=True, samesite="lax")
    response.set_cookie(
        "csrftoken", "lite-csrf-token", httponly=False, samesite="lax",
    )
    return {"error": None, "data": {"username": username}}


# ── logout ─────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("lite_user")
    return {"error": None, "data": "ok"}
