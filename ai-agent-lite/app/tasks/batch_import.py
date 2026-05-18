"""Celery task for batch problem import with progress tracking.

Processes parsed problems one by one, updating progress in Redis
so the status polling endpoint can report real-time results.
"""

import logging
import traceback
import uuid
from typing import Any

from app.celery_app import celery_app
from app.config import settings
from app.services.problem_import import detect_format, parse_fps_xml, parse_hydro_zip
from app.services.problem_service import create_problem

logger = logging.getLogger("ai-agent-lite.batch_import_task")

# Progress is stored in Redis as a JSON dict keyed by task_id
# We use Celery's backend (Redis) for this — set/get via the result backend.

import json
import redis

def _get_redis() -> redis.Redis:
    """Get a Redis client from the Celery backend URL."""
    url = settings.celery_result_backend
    return redis.from_url(url)


def _init_progress(task_id: str, total: int) -> None:
    """Initialize progress tracker in Redis."""
    r = _get_redis()
    key = f"import_progress:{task_id}"
    r.set(key, json.dumps({
        "task_id": task_id,
        "status": "running",
        "total": total,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "failed_details": [],
    }, ensure_ascii=False))


def _update_progress(task_id: str, **kwargs) -> None:
    """Update progress fields in Redis."""
    r = _get_redis()
    key = f"import_progress:{task_id}"
    raw = r.get(key)
    if not raw:
        return
    data = json.loads(raw)
    data.update(kwargs)
    r.set(key, json.dumps(data, ensure_ascii=False))


def _finalize_progress(task_id: str, status: str) -> None:
    """Set final status and expire the key after 1 hour."""
    r = _get_redis()
    key = f"import_progress:{task_id}"
    raw = r.get(key)
    if not raw:
        return
    data = json.loads(raw)
    data["status"] = status
    r.set(key, json.dumps(data, ensure_ascii=False))
    r.expire(key, 3600)  # auto-cleanup after 1h


def get_import_progress(task_id: str) -> dict | None:
    """Read import progress from Redis (used by the status endpoint)."""
    r = _get_redis()
    key = f"import_progress:{task_id}"
    raw = r.get(key)
    if not raw:
        return None
    return json.loads(raw)


@celery_app.task(bind=True, queue="audit", max_retries=1)
def batch_import_problems(self, file_path: str, fmt: str, extra_tags: list[str] | None = None,
                          difficulty_override: str | None = None, visible: bool = False) -> dict:
    """Celery task: parse problem file and import all problems via direct DB write.

    Args:
        file_path: Absolute path to the uploaded file (on shared volume).
        fmt: "fps" or "hydro".
        extra_tags: Additional tags to append to every problem.
        difficulty_override: Override all problems' difficulty (e.g. "Mid").
        visible: Whether to set problems as visible after import.

    Returns:
        Summary dict with total/imported/skipped/failed counts.
    """
    import psycopg2
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

    task_id = self.request.id

    # Step 1: Parse the file
    try:
        if fmt == "fps":
            problems = parse_fps_xml(file_path)
        elif fmt == "hydro":
            problems = parse_hydro_zip(file_path)
        else:
            raise ValueError(f"Unknown format: {fmt}")
    except Exception as e:
        logger.error("Failed to parse import file: %s", e)
        _init_progress(task_id, 0)
        _finalize_progress(task_id, "failed")
        return {"error": str(e), "total": 0, "imported": 0}

    total = len(problems)
    _init_progress(task_id, total)

    if total == 0:
        _finalize_progress(task_id, "completed")
        return {"total": 0, "imported": 0, "skipped": 0, "failed": 0}

    # Step 2: Import each problem (sync wrapper around async DB calls)
    imported = 0
    skipped = 0
    failed = 0
    failed_details = []

    # Use sync psycopg2 for simplicity in Celery worker context
    db_url = settings.db_url.replace("+asyncpg", "")
    conn = psycopg2.connect(db_url)

    try:
        for i, prob in enumerate(problems):
            try:
                # Apply overrides
                if difficulty_override:
                    prob["difficulty"] = difficulty_override
                if extra_tags:
                    existing_tags = prob.get("tags", [])
                    prob["tags"] = list(set(existing_tags + extra_tags))
                prob["visible"] = visible

                # Check if problem with same title already exists
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM problem WHERE title = %s LIMIT 1", (prob["title"].strip(),))
                    if cur.fetchone():
                        skipped += 1
                        _update_progress(task_id, imported=imported, skipped=skipped, failed=failed)
                        logger.info("Skipped duplicate: '%s'", prob["title"])
                        continue

                # Insert problem
                result = _insert_problem_sync(conn, prob)
                imported += 1
                _update_progress(task_id, imported=imported, skipped=skipped, failed=failed)
                logger.info("Imported %d/%d: '%s' (id=%s)", imported, total, prob["title"], result.get("_id"))

            except Exception as e:
                failed += 1
                failed_details.append({"title": prob.get("title", "?"), "reason": str(e)})
                _update_progress(
                    task_id,
                    imported=imported,
                    skipped=skipped,
                    failed=failed,
                    failed_details=failed_details,
                )
                logger.warning("Failed to import '%s': %s", prob.get("title", "?"), e)
                conn.rollback()
                continue

        conn.commit()
    finally:
        conn.close()

    # Cleanup uploaded file
    try:
        import os
        os.unlink(file_path)
    except Exception:
        pass

    _finalize_progress(task_id, "completed")

    return {
        "total": total,
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "failed_details": failed_details,
    }


def _insert_problem_sync(conn, prob: dict) -> dict:
    """Synchronous DB insert for a single problem (used in Celery worker)."""
    import hashlib
    import json
    import os
    import uuid
    from pathlib import Path

    from app.services.problem_service import (
        DEFAULT_LANGUAGES,
        TEST_CASE_DIR,
        VALID_DIFFICULTIES,
        VALID_RULE_TYPES,
        generate_problem_id,
        write_test_case_files,
    )

    title = prob["title"].strip()
    _id = prob.get("_id") or generate_problem_id()
    difficulty = prob.get("difficulty", "Low")
    if difficulty not in VALID_DIFFICULTIES:
        difficulty = "Low"
    rule_type = prob.get("rule_type", "ACM")
    if rule_type not in VALID_RULE_TYPES:
        rule_type = "ACM"
    languages = prob.get("languages", DEFAULT_LANGUAGES)
    samples = prob.get("samples", [])
    test_cases = prob.get("test_cases", [])

    # Write test case files
    test_case_id = _id  # fallback
    test_case_score = []

    if test_cases:
        # Write to a temp dir first, compute the MD5 from info file,
        # then rename to the MD5-named directory (legacy judge convention).
        import tempfile
        with tempfile.TemporaryDirectory(prefix="tc_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            tc_id, test_case_score = write_test_case_files(tmp_path, test_cases)
            final_dir = TEST_CASE_DIR / tc_id
            if not final_dir.exists():
                import shutil
                shutil.copytree(tmp_path, final_dir)
            test_case_id = tc_id

    # Insert problem row
    # Note: psycopg2 supports %s::jsonb cast syntax, this is fine.
    # Note: legacy OJ column names: create_time/last_update_time (not created_at)
    # Note: Several NOT NULL columns need defaults: template, statistic_info, etc.
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO problem (
                _id, title, description, input_description, output_description,
                samples, hint, source, difficulty, rule_type,
                time_limit, memory_limit, languages, template,
                test_case_id, test_case_score,
                visible, is_public, created_by_id, create_time, last_update_time,
                contest_id, spj, spj_compile_ok, io_mode, total_score,
                statistic_info, submission_number, accepted_number, share_submission
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s::jsonb, %s, %s, %s, %s,
                %s, %s, %s::jsonb, %s::jsonb,
                %s, %s::jsonb,
                %s, %s, 1, NOW(), NOW(),
                NULL, false, false, '{"io_mode":"Standard I/O"}'::jsonb, %s,
                %s::jsonb, 0, 0, false
            ) RETURNING id, _id
        """, (
            _id, title,
            prob.get("description", ""),
            prob.get("input_description", ""),
            prob.get("output_description", ""),
            json.dumps(samples, ensure_ascii=False),
            prob.get("hint", ""),
            prob.get("source", ""),
            difficulty,
            rule_type,
            prob.get("time_limit", 1000),
            prob.get("memory_limit", 256),
            json.dumps(languages, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),  # template
            test_case_id,
            json.dumps(test_case_score, ensure_ascii=False) if test_case_score else "[]",
            prob.get("visible", False),
            prob.get("visible", False),
            sum(tc.get("score", 0) for tc in test_cases) or 100,
            json.dumps({}, ensure_ascii=False),  # statistic_info
        ))
        row = cur.fetchone()
        db_id = row[0]
        returned_id = row[1]

        # Link tags
        tags = prob.get("tags", [])
        for tag_name in tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            cur.execute("SELECT id FROM problem_tag WHERE name = %s", (tag_name,))
            tag_row = cur.fetchone()
            if not tag_row:
                cur.execute(
                    "INSERT INTO problem_tag (name) VALUES (%s) RETURNING id",
                    (tag_name,),
                )
                tag_row = cur.fetchone()
            tag_id = tag_row[0]
            cur.execute(
                "INSERT INTO problem_tags (problem_id, problemtag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (db_id, tag_id),
            )

    return {"id": db_id, "_id": returned_id}
