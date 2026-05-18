"""Background Celery task: problem quality auditor.

Audits local (custom-*) OJ problems via a configurable LLM backend,
evaluating completeness, removing non-OJ content, deduplicating garbage,
reclassifying difficulty, and adding algorithmic tags.

Architecture:
  problem_auditor.py   — Celery task entrypoints (thin)
  audit/db.py          — psycopg2 database layer
  audit/llm.py         — LLM provider dispatch + prompt building
  audit/classifier.py  — heuristic checks, marker wrapping, fix application
"""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from app.tasks.audit import db, llm, classifier

logger = logging.getLogger("ai-agent-lite.audit")


# ═══════════════════════════════════════════════════════════════════════
# Core audit logic (shared by single + batch + beat tasks)
# ═══════════════════════════════════════════════════════════════════════

def _do_audit_problem(
    display_id: str, db_id: int, title: str, retry=None,
) -> dict:
    """Core audit logic for a single problem."""
    logger.info(
        "Auditing _id=%s (db_id=%d, title=%s)", display_id, db_id, title,
    )

    try:
        problem = db.fetch_problem_detail(db_id)
        if problem is None:
            return {
                "_id": display_id, "status": "error",
                "message": "Failed to fetch detail",
            }
    except Exception as exc:
        logger.exception("PG fetch failed _id=%s", display_id)
        if retry:
            raise retry.retry(exc=exc)
        raise

    prompt = llm.build_audit_prompt(problem)
    try:
        raw = llm.call_llm(llm.AUDIT_SYSTEM_PROMPT, prompt)
    except Exception as exc:
        logger.exception("Audit LLM call failed _id=%s", display_id)
        if retry:
            raise retry.retry(exc=exc)
        raise

    result = llm.parse_llm_response(raw)

    status = result.get("status", "error")
    issues = result.get("issues", [])
    fixes = result.get("fixes", {}) or {}

    if status == "remove":
        reason = result.get("reason", "Non-OJ problem")
        logger.info("REMOVE %s: %s", display_id, reason)
        db.upsert_audit_record(display_id, db_id, "remove", [reason], {}, raw)
        return {"_id": display_id, "status": "remove", "issues": [reason]}

    db.upsert_audit_record(display_id, db_id, status, issues, fixes, raw)

    if status == "fail" and fixes:
        try:
            classifier.apply_fixes(problem, fixes)
            logger.info("Auto-fixed _id=%s", display_id)
        except Exception:
            logger.exception("Auto-fix failed _id=%s", display_id)
            db.upsert_audit_record(
                display_id, db_id, "fix_failed", issues, fixes, raw,
            )

    return {"_id": display_id, "status": status, "issues": issues}


# ═══════════════════════════════════════════════════════════════════════
# Celery tasks
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(
    name="app.tasks.problem_auditor.audit_single_problem",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="audit",
    soft_time_limit=300,
    time_limit=360,
)
def audit_single_problem(self, problem_summary: dict) -> dict:
    """Audit a single problem via the configured audit LLM and auto-fix if needed."""
    display_id = problem_summary["_id"]
    db_id = int(problem_summary.get("id") or 0)
    title = problem_summary.get("title", display_id)

    if db_id == 0:
        try:
            db_id = db.resolve_db_id(display_id)
            if db_id:
                detail = db.fetch_problem_detail(db_id)
                title = (detail or {}).get("title") or display_id
                logger.info(
                    "Resolved display_id=%s -> db_id=%d", display_id, db_id,
                )
            else:
                logger.error(
                    "Cannot resolve db_id for display_id=%s", display_id,
                )
                return {
                    "_id": display_id, "status": "error",
                    "message": "Not found in problem table",
                }
        except Exception as exc:
            logger.error(
                "Failed to resolve db_id for %s: %s", display_id, exc,
            )
            return {
                "_id": display_id, "status": "error",
                "message": f"resolve: {exc}",
            }

    return _do_audit_problem(display_id, db_id, title, retry=self)


@celery_app.task(
    name="app.tasks.problem_auditor.clean_problem_statement",
    queue="audit",
    soft_time_limit=300,
    time_limit=360,
)
def clean_problem_statement(problem_summary: dict) -> dict:
    """Compatibility task for /audit/clean endpoint."""
    display_id = problem_summary.get("_id")
    if not display_id:
        return {"status": "error", "message": "missing _id"}
    result = audit_single_problem.apply(
        args=({"id": 0, "_id": display_id, "title": ""},),
    )
    return result.get() if hasattr(result, "get") else {
        "status": "queued", "_id": display_id,
    }


@celery_app.task(
    name="app.tasks.problem_auditor.audit_next_problem",
    queue="audit",
    soft_time_limit=300,
    time_limit=360,
)
def audit_next_problem() -> dict:
    """Find and audit ONE un-audited local problem via PostgreSQL.

    Beat fires every 100s, so ~3 audits / 5 min.
    """
    problem = db.get_next_local_unaudited()
    if problem is None:
        logger.info("No un-audited local problems — all done")
        return {
            "status": "no_work",
            "message": "All local problems audited",
        }

    display_id = problem["_id"]
    db_id = problem["id"]
    title = problem.get("title", display_id)

    db._in_flight_ids.add(display_id)
    try:
        logger.info(
            "Beat tick: auditing _id=%s (db_id=%d)", display_id, db_id,
        )
        return _do_audit_problem(display_id, db_id, title)
    finally:
        db._in_flight_ids.discard(display_id)


@celery_app.task(
    name="app.tasks.problem_auditor.audit_all_problems",
    bind=True,
    queue="audit",
    soft_time_limit=7200,
    time_limit=7800,
)
def audit_all_problems(self, force: bool = False, limit: int = 0) -> dict:
    """Orchestrate batch audit of all local problems."""
    batch_id = str(uuid.uuid4())[:8]
    logger.info(
        "Batch %s started (force=%s, limit=%s)", batch_id, force, limit,
    )

    all_local = db.get_all_local_problems()
    logger.info("Batch %s: %d local problems total", batch_id, len(all_local))

    if not force:
        audited = db.get_all_audited_ids()
        targets = [p for p in all_local if p["_id"] not in audited]
        logger.info(
            "Batch %s: %d need auditing (already passed: %d)",
            batch_id, len(targets), len(audited),
        )
    else:
        targets = all_local

    if limit > 0 and len(targets) > limit:
        targets = targets[:limit]

    if not targets:
        return {
            "batch_id": batch_id, "total": len(all_local),
            "dispatched": 0,
            "message": "All local problems already audited",
        }

    task_ids = []
    for i, p in enumerate(targets):
        summary = {
            "_id": p["_id"], "id": p["id"],
            "title": p.get("title", ""),
        }
        r = audit_single_problem.apply_async(
            args=(summary,), queue="audit", countdown=i * 110,
        )
        task_ids.append(r.id)

    logger.info("Batch %s: dispatched %d tasks", batch_id, len(task_ids))
    return {
        "batch_id": batch_id, "total": len(all_local),
        "dispatched": len(task_ids),
        "task_ids": task_ids[:50],
    }


@celery_app.task(
    name="app.tasks.problem_auditor.reset_audit_state",
    queue="audit",
)
def reset_audit_state() -> dict:
    """Clear all audit records so everything gets re-audited."""
    deleted = db.clear_all_audit_records()
    total = db.get_local_problem_count()
    return {
        "deleted_records": deleted,
        "local_problems": total,
        "message": (
            f"Cleared {deleted} records. "
            f"{total} local problems ready for re-audit."
        ),
    }
