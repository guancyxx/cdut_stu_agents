"""PostgreSQL helpers for the problem auditor.

Synchronous psycopg2-based queries and writes to the OJ database.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger("ai-agent-lite.audit.db")

# In-memory dedup: prevent overlapping Beat ticks from double-auditing.
_in_flight_ids: set[str] = set()


def pg_connect():
    """Return a psycopg2 connection to the OJ database."""
    import psycopg2
    db_url = settings.db_url.replace("+asyncpg", "")
    return psycopg2.connect(db_url)


def problem_prefix_filter_clause(column: str = "p._id") -> tuple[str, tuple]:
    """Build optional SQL filter for problem display-id prefix."""
    prefix = settings.audit_problem_id_prefix
    if not prefix:
        return "", ()
    return f"AND {column} LIKE %s", (f"{prefix}%",)


def resolve_db_id(display_id: str) -> int:
    """Resolve problem DB id from display id (_id)."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM problem WHERE _id = %s LIMIT 1", (display_id,),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        conn.close()


def fetch_problem_detail(db_id: int) -> dict | None:
    """Fetch full problem row and normalize fields used by auditor."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, _id, title, description, input_description, "
                "output_description, samples, hint, languages, template, "
                "time_limit, memory_limit, rule_type, spj, visible, "
                "difficulty, source, test_case_id, io_mode "
                "FROM problem WHERE id = %s LIMIT 1",
                (db_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            keys = [
                "id", "_id", "title", "description", "input_description",
                "output_description", "samples", "hint", "languages",
                "template", "time_limit", "memory_limit", "rule_type",
                "spj", "visible", "difficulty", "source", "test_case_id",
                "io_mode",
            ]
            data = dict(zip(keys, row))
            for key in ("samples", "languages", "template", "io_mode"):
                if data.get(key) is None:
                    data[key] = {} if key in ("template", "io_mode") else []
            return data
    finally:
        conn.close()


def ensure_tag_ids(tags: list[str]) -> list[int]:
    """Ensure tags exist in problem_tag table and return their ids."""
    if not tags:
        return []

    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            ids: list[int] = []
            for raw in tags:
                name = (raw or "").strip()
                if not name:
                    continue
                cur.execute(
                    "SELECT id FROM problem_tag WHERE name = %s LIMIT 1",
                    (name,),
                )
                row = cur.fetchone()
                if row:
                    ids.append(int(row[0]))
                    continue
                cur.execute(
                    "INSERT INTO problem_tag (name) VALUES (%s) RETURNING id",
                    (name,),
                )
                ids.append(int(cur.fetchone()[0]))
            conn.commit()
            return ids
    finally:
        conn.close()


def update_problem(payload: dict) -> bool:
    """Update problem via direct PostgreSQL write."""
    problem_id = payload.get("id")
    if not problem_id:
        return False

    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE problem SET title=%s, description=%s, "
                "input_description=%s, output_description=%s, "
                "samples=%s::jsonb, hint=%s, languages=%s::jsonb, "
                "template=%s::jsonb, difficulty=%s, source=%s, "
                "last_update_time=%s WHERE id=%s",
                (
                    payload.get("title", ""),
                    payload.get("description", ""),
                    payload.get("input_description", ""),
                    payload.get("output_description", ""),
                    json.dumps(payload.get("samples") or [], ensure_ascii=False),
                    payload.get("hint"),
                    json.dumps(payload.get("languages") or [], ensure_ascii=False),
                    json.dumps(payload.get("template") or {}, ensure_ascii=False),
                    payload.get("difficulty", "Low"),
                    payload.get("source"),
                    datetime.now(timezone.utc),
                    int(problem_id),
                ),
            )

            if payload.get("tags") is not None:
                tag_ids = ensure_tag_ids(list(payload.get("tags") or []))
                cur.execute(
                    "DELETE FROM problem_tags WHERE problem_id = %s",
                    (int(problem_id),),
                )
                for tag_id in tag_ids:
                    cur.execute(
                        "INSERT INTO problem_tags (problem_id, problemtag_id) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (int(problem_id), int(tag_id)),
                    )

            conn.commit()
            return True
    except Exception:
        conn.rollback()
        logger.exception("Problem update failed id=%s", problem_id)
        return False
    finally:
        conn.close()


def get_all_audited_ids() -> set[str]:
    """Return set of problem display_ids that already passed audit."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            prefix_clause, prefix_params = problem_prefix_filter_clause(
                "pa.problem_display_id",
            )
            cur.execute(
                (
                    "SELECT pa.problem_display_id "
                    "FROM {schema}.problem_audit pa "
                    "WHERE pa.status = 'pass' {prefix_clause}"
                ).format(schema=settings.db_schema, prefix_clause=prefix_clause),
                prefix_params,
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def get_next_local_unaudited() -> dict | None:
    """Find ONE problem not yet audited, via PostgreSQL."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            in_flight_clause = ""
            in_flight_params = ()
            if _in_flight_ids:
                placeholders = ",".join(["%s"] * len(_in_flight_ids))
                in_flight_clause = f"AND p._id NOT IN ({placeholders})"
                in_flight_params = tuple(sorted(_in_flight_ids))

            prefix_clause, prefix_params = problem_prefix_filter_clause("p._id")
            query = (
                "SELECT p.id, p._id, p.title FROM problem p "
                "WHERE 1=1 {prefix_clause} "
                "AND p._id NOT IN ("
                "    SELECT problem_display_id"
                "    FROM {schema}.problem_audit"
                ") {in_flight} "
                "ORDER BY p.id LIMIT 1"
            ).format(
                schema=settings.db_schema,
                in_flight=in_flight_clause,
                prefix_clause=prefix_clause,
            )
            params = prefix_params + in_flight_params
            cur.execute(query, params)
            row = cur.fetchone()
            if row:
                return {"id": row[0], "_id": row[1], "title": row[2]}
            return None
    finally:
        conn.close()


def get_all_local_problems() -> list[dict]:
    """Return all scoped problems (id, _id, title) via PostgreSQL."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            prefix_clause, prefix_params = problem_prefix_filter_clause("_id")
            query = (
                "SELECT id, _id, title FROM problem "
                "WHERE 1=1 {prefix_clause} ORDER BY id"
            ).format(prefix_clause=prefix_clause)
            cur.execute(query, prefix_params)
            return [
                {"id": r[0], "_id": r[1], "title": r[2]}
                for r in cur.fetchall()
            ]
    finally:
        conn.close()


def get_local_problem_count() -> int:
    """Count how many scoped problems exist."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            prefix_clause, prefix_params = problem_prefix_filter_clause("_id")
            query = (
                "SELECT count(*) FROM problem WHERE 1=1 {prefix_clause}"
            ).format(prefix_clause=prefix_clause)
            cur.execute(query, prefix_params)
            return cur.fetchone()[0]
    finally:
        conn.close()


def upsert_audit_record(
    display_id: str,
    db_id: int,
    audit_status: str,
    issues: list,
    fixes: dict,
    llm_raw: str,
    extra: dict | None = None,
) -> None:
    """Insert or update an audit record."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "SELECT id FROM {schema}.problem_audit "
                    "WHERE problem_display_id = %s "
                    "ORDER BY created_at DESC LIMIT 1"
                ).format(schema=settings.db_schema),
                (display_id,),
            )
            existing = cur.fetchone()

            now = datetime.now(timezone.utc)
            issues_j = json.dumps(issues, ensure_ascii=False)
            fixes_j = json.dumps(fixes, ensure_ascii=False)

            if existing:
                cur.execute(
                    (
                        "UPDATE {schema}.problem_audit SET "
                        "status=%s, issues=%s, fixes=%s, llm_raw_response=%s, "
                        "updated_at=%s WHERE id=%s"
                    ).format(schema=settings.db_schema),
                    (audit_status, issues_j, fixes_j, llm_raw, now, existing[0]),
                )
            else:
                cur.execute(
                    (
                        "INSERT INTO {schema}.problem_audit "
                        "(problem_display_id, problem_db_id, status, issues, "
                        " fixes, llm_raw_response, created_at, updated_at) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    ).format(schema=settings.db_schema),
                    (display_id, db_id, audit_status,
                     issues_j, fixes_j, llm_raw, now, now),
                )
            conn.commit()
    finally:
        conn.close()


def delete_audit_record(display_id: str) -> None:
    """Remove all audit records for a problem (allows re-audit)."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "DELETE FROM {schema}.problem_audit "
                    "WHERE problem_display_id = %s"
                ).format(schema=settings.db_schema),
                (display_id,),
            )
            conn.commit()
    finally:
        conn.close()


def clear_all_audit_records() -> int:
    """Delete ALL audit records. Returns count of deleted rows."""
    conn = pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM {schema}.problem_audit".format(
                    schema=settings.db_schema,
                ),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted
    finally:
        conn.close()
