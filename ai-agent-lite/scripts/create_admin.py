#!/usr/bin/env python3
"""Bootstrap the first super-admin account.

Usage (from ai-agent-lite/):
    python scripts/create_admin.py [username] [password]

Defaults: admin / cdut_oj_2026

Idempotent: if the username already exists the script prints a message and exits 0.
"""
import asyncio
import base64
import hashlib
import os
import secrets
import sys
from datetime import datetime, timezone

import asyncpg

_RAW_URL = os.getenv(
    "LITE_DATABASE_URL",
    "postgresql+asyncpg://cdut:cdut_oj_2024@cdut-postgres:5432/cdut_oj",
)
_DSN = _RAW_URL.replace("postgresql+asyncpg://", "postgresql://")
_SCHEMA = os.getenv("LITE_DB_SCHEMA", "ai_agent")


def _hash_password(raw: str) -> str:
    iterations = 260000
    salt = secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), iterations)
    digest = base64.b64encode(dk).decode().strip()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


async def main(username: str, password: str) -> None:
    conn = await asyncpg.connect(_DSN)
    try:
        now = datetime.now(timezone.utc)
        result = await conn.fetchval(
            f"INSERT INTO {_SCHEMA}.local_users"
            "  (username, password_hash, admin_type, created_at, updated_at)"
            " VALUES ($1, $2, 2, $3, $3)"
            " ON CONFLICT (username) DO NOTHING"
            " RETURNING username",
            username, _hash_password(password), now,
        )
        if result:
            print(f"Created super-admin: {username}")
        else:
            print(f"Username '{username}' already exists — skipped.")
    finally:
        await conn.close()


if __name__ == "__main__":
    _u = sys.argv[1] if len(sys.argv) > 1 else "admin"
    _p = sys.argv[2] if len(sys.argv) > 2 else "cdut_oj_2026"
    asyncio.run(main(_u, _p))
