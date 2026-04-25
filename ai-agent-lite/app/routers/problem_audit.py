"""REST API endpoints for problem quality audit.

Provides endpoints to:
- Trigger batch audit of all (or un-audited) problems
- Trigger single-problem audit
- Query audit status/results
- Force re-audit of all problems
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.celery_app import celery_app
from app.tasks.problem_auditor import audit_single_problem, audit_all_problems

logger = logging.getLogger("ai-agent-lite.audit_api")

router = APIRouter(prefix="/audit", tags=["audit"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AuditTriggerResponse(BaseModel):
    """Response model for audit trigger endpoints."""
    task_id: str
    message: str


class AuditStatusResponse(BaseModel):
    """Response model for audit status queries."""
    task_id: str
    status: str
    result: dict | None = None


class BatchAuditSummary(BaseModel):
    """Summary of the last batch audit."""
    total_problems: int
    audited: int
    passed: int
    failed: int
    errors: int
    last_audit_time: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run", response_model=AuditTriggerResponse)
async def trigger_audit(
    force: bool = Query(False, description="Force re-audit all problems"),
    limit: int = Query(0, ge=0, description="Max problems to audit. 0 = use default batch size (50)"),
):
    """Trigger a batch audit of all (or all un-audited) problems.

    With force=false (default): only audits problems that have no pass record.
    With force=true: re-audits all problems regardless.
    limit=0 means use the default audit_batch_size from config (50).
    """
    task = audit_all_problems.apply_async(kwargs={"force": force, "limit": limit}, queue="audit")
    logger.info("Triggered batch audit task_id=%s force=%s limit=%s", task.id, force, limit)
    return AuditTriggerResponse(
        task_id=task.id,
        message=f"Batch audit {'(force)' if force else ''} started (limit={limit or 'default'})",
    )


@router.post("/run/{problem_display_id}", response_model=AuditTriggerResponse)
async def trigger_single_audit(problem_display_id: str):
    """Trigger audit for a single problem by its display ID (e.g. 'custom-ab1c')."""
    # We need the db_id — fetch it via the OJ API inside the task
    task = audit_single_problem.apply_async(
        args=({"_id": problem_display_id, "id": 0, "title": ""},),
        queue="audit",
    )
    logger.info("Triggered single audit task_id=%s problem=%s", task.id, problem_display_id)
    return AuditTriggerResponse(
        task_id=task.id,
        message=f"Single audit started for problem {problem_display_id}",
    )


@router.get("/status/{task_id}", response_model=AuditStatusResponse)
async def get_audit_status(task_id: str):
    """Query the status of a running or completed audit task."""
    result = celery_app.AsyncResult(task_id)
    response = AuditStatusResponse(
        task_id=task_id,
        status=result.status,
        result=None,
    )
    if result.status == "SUCCESS":
        response.result = result.result
    elif result.status == "FAILURE":
        response.result = {"error": str(result.result)}
    return response


@router.get("/records")
async def list_audit_records(
    status: str | None = Query(None, description="Filter by status: pass, fail, error, fix_failed"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List audit records from the database."""
    from app.config import settings
    import psycopg2
    import json

    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            where_clause = ""
            params = []
            if status:
                where_clause = "WHERE status = %s"
                params.append(status)

            cur.execute(
                "SELECT problem_display_id, problem_db_id, status, issues, fixes, "
                "created_at, updated_at "
                f"FROM {settings.db_schema}.problem_audit {where_clause} "
                "ORDER BY updated_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset],
            )
            rows = cur.fetchall()
            records = []
            for row in rows:
                records.append({
                    "problem_display_id": row[0],
                    "problem_db_id": row[1],
                    "status": row[2],
                    "issues": row[3] if isinstance(row[3], list) else json.loads(row[3]) if row[3] else [],
                    "fixes": row[4] if isinstance(row[4], dict) else json.loads(row[4]) if row[4] else {},
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                })
            return {"total": len(records), "records": records}
    finally:
        conn.close()


@router.get("/summary")
async def audit_summary():
    """Return a summary of the last batch audit results."""
    from app.config import settings
    import psycopg2

    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT status, COUNT(*) FROM {settings.db_schema}.problem_audit "
                "GROUP BY status"
            )
            counts = {row[0]: row[1] for row in cur.fetchall()}
            cur.execute(
                f"SELECT MAX(updated_at) FROM {settings.db_schema}.problem_audit"
            )
            last_time = cur.fetchone()[0]
            cur.execute(
                f"SELECT COUNT(*) FROM {settings.db_schema}.problem_audit"
            )
            total = cur.fetchone()[0]

        return {
            "total_problems": total,
            "passed": counts.get("pass", 0),
            "failed": counts.get("fail", 0),
            "errors": counts.get("error", 0) + counts.get("fix_failed", 0),
            "pending": counts.get("pending", 0),
            "last_audit_time": last_time.isoformat() if last_time else None,
        }
    finally:
        conn.close()


@router.delete("/records/{problem_display_id}")
async def delete_audit_record(problem_display_id: str):
    """Delete audit record for a specific problem (allows re-audit)."""
    from app.config import settings
    import psycopg2

    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {settings.db_schema}.problem_audit "
                "WHERE problem_display_id = %s",
                (problem_display_id,),
            )
            deleted = cur.rowcount
            conn.commit()
        return {"deleted": deleted, "problem_display_id": problem_display_id}
    finally:
        conn.close()