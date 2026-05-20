"""Shared authentication helpers for the compat OJ API routes.

Extracted from compat_oj_api.py to keep individual route modules small
and avoid circular imports.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets

from fastapi import HTTPException, Request
from sqlalchemy import text

from app.database import async_session

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PEPPER = os.getenv("LITE_AUTH_PEPPER", "cdut-lite-pepper")


def hash_password(raw: str) -> str:
    """Generate Django-compatible PBKDF2-SHA256 hash string."""
    iterations = 260000
    salt = secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac(
        "sha256", raw.encode("utf-8"), salt.encode("utf-8"), iterations,
    )
    digest = base64.b64encode(dk).decode("ascii").strip()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(raw: str, stored: str) -> bool:
    """Verify both legacy pepper-sha256 and Django pbkdf2 hashes."""
    if not stored:
        return False

    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iter_str, salt, digest = stored.split("$", 3)
            iterations = int(iter_str)
            dk = hashlib.pbkdf2_hmac(
                "sha256", raw.encode("utf-8"), salt.encode("utf-8"), iterations,
            )
            calc = base64.b64encode(dk).decode("ascii").strip()
            return hmac.compare_digest(calc, digest)
        except Exception:
            return False

    payload = f"{PEPPER}:{raw}".encode("utf-8")
    return hmac.compare_digest(hashlib.sha256(payload).hexdigest(), stored)


def captcha_svg_data_url() -> str:
    """Generate a visible inline SVG captcha data URL for compat UI."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    captcha_text = "".join(secrets.choice(alphabet) for _ in range(4))

    noise = "".join(
        f'<line x1="{i * 17 + 8}" y1="6" x2="{(i + 1) * 19}" y2="38"'
        f' stroke="#9ca3af" stroke-width="1" opacity="0.35" />'
        for i in range(3)
    )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="44" viewBox="0 0 100 44">'
        '<rect width="100" height="44" rx="6" fill="#111827" />'
        f"{noise}"
        f'<text x="50" y="29" text-anchor="middle" fill="#f9fafb" '
        'font-family="monospace" font-size="22" font-weight="700" letter-spacing="3">'
        f"{captcha_text}"
        "</text>"
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def current_username(request: Request) -> str | None:
    """Extract username from the lite_user cookie."""
    return request.cookies.get("lite_user")


async def require_admin_username(request: Request) -> str:
    """Check that the current user has admin_type >= 1 and is not disabled.

    Raises 401/403.
    """
    username = current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Please login first")

    async with async_session() as db:
        row = (
            await db.execute(
                text(
                    "SELECT COALESCE(admin_type,0), COALESCE(is_disabled,false) "
                    "FROM ai_agent.local_users WHERE username=:u LIMIT 1",
                ),
                {"u": username},
            )
        ).fetchone()

    if not row:
        raise HTTPException(status_code=403, detail="Admin permission required")
    if row[1]:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if int(row[0] or 0) < 1:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return username
