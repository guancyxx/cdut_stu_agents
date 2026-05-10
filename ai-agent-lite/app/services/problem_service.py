"""Problem creation service — direct DB write for QDUOJ problem table.

Avoids the QDUOJ Admin API entirely (CSRF complexity, ~3 HTTP calls/problem).
Writes directly to public.problem, public.problem_tag, public.problem_tags.
Test case files go to the shared volume /data/test_case/.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger("ai-agent-lite.problem_service")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_CASE_DIR = Path(os.getenv("TEST_CASE_DIR", "/data/test_case"))

DEFAULT_LANGUAGES = ["C", "C++", "Java", "Python3"]
VALID_DIFFICULTIES = {"Low", "Mid", "High"}
VALID_RULE_TYPES = {"ACM", "OI"}


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def generate_problem_id(prefix: str = "custom") -> str:
    """Generate a unique _id like 'custom-a3f1'."""
    short = uuid.uuid4().hex[:4]
    return f"{prefix}-{short}"


def compute_test_case_id(test_case_dir: Path) -> str:
    """Compute the test_case_id (MD5 of the info file content).

    QDUOJ uses the MD5 of the info file as the test_case_id.
    If no info file exists yet, generate a fresh MD5 from uuid4.
    """
    info_path = test_case_dir / "info"
    if info_path.exists():
        return hashlib.md5(info_path.read_bytes()).hexdigest()
    return hashlib.md5(uuid.uuid4().bytes).hexdigest()


# ---------------------------------------------------------------------------
# Test-case file I/O
# ---------------------------------------------------------------------------

def write_test_case_files(
    test_case_dir: Path,
    test_cases: list[dict],
) -> tuple[str, list[dict]]:
    """Write test case in/out files and info manifest to disk.

    Args:
        test_case_dir: Target directory (will be created if needed).
        test_cases: List of {"input": str, "output": str} dicts.

    Returns:
        (test_case_id, test_case_score)
        test_case_id: MD5 hash string used as the directory name under /data/test_case/
        test_case_score: [{"score": N}, ...] one entry per test case
    """
    os.makedirs(test_case_dir, exist_ok=True)

    info_test_cases = {}
    test_case_score = []

    for idx, tc in enumerate(test_cases):
        input_name = f"{idx + 1}.in"
        output_name = f"{idx + 1}.out"

        input_bytes = tc["input"].encode("utf-8") if isinstance(tc["input"], str) else tc["input"]
        output_bytes = tc["output"].encode("utf-8") if isinstance(tc["output"], str) else tc["output"]

        (test_case_dir / input_name).write_bytes(input_bytes)
        (test_case_dir / output_name).write_bytes(output_bytes)

        info_test_cases[str(idx)] = {
            "input_size": len(input_bytes),
            "input_name": input_name,
            "output_size": len(output_bytes),
            "output_name": output_name,
            "stripped_output_md5": hashlib.md5(output_bytes.strip()).hexdigest(),
        }

        # Default: equal score per test case (100 total / N)
        score = tc.get("score", 0)
        test_case_score.append({"score": score} if score else {"score": 0})

    # Distribute total score = 100 evenly across test cases
    n = len(test_cases)
    if n > 0:
        base_score = 100 // n
        remainder = 100 % n
        test_case_score = []
        for i in range(n):
            test_case_score.append({"score": base_score + (1 if i < remainder else 0)})

    # Write info file
    info_data = {
        "spj": False,
        "test_cases": info_test_cases,
    }
    info_json = json.dumps(info_data, ensure_ascii=False)
    (test_case_dir / "info").write_text(info_json, encoding="utf-8")

    test_case_id = hashlib.md5(info_json.encode("utf-8")).hexdigest()
    return test_case_id, test_case_score


# ---------------------------------------------------------------------------
# Problem CRUD (direct DB)
# ---------------------------------------------------------------------------

async def create_problem(
    session: AsyncSession,
    *,
    title: str,
    description: str = "",
    input_description: str = "",
    output_description: str = "",
    samples: list[dict] | None = None,
    hint: str = "",
    source: str = "",
    difficulty: str = "Low",
    rule_type: str = "ACM",
    time_limit: int = 1000,
    memory_limit: int = 256,
    languages: list[str] | None = None,
    visible: bool = False,
    tags: list[str] | None = None,
    test_cases: list[dict] | None = None,
    created_by_id: int = 1,
    _id: str | None = None,
) -> dict:
    """Insert a problem row directly into public.problem and return the result.

    If test_cases is provided, writes the test case files to disk and fills
    test_case_id / test_case_score.

    Args:
        session: Async SQLAlchemy session.
        title: Problem title (required).
        _id: Override display ID or auto-generate.
        created_by_id: Must reference a valid user.id (default: 1 = root).
        test_cases: Optional list of {"input": ..., "output": ..., "score": ...}.
        tags: Optional list of tag names to link (e.g. ["数学", "动态规划"]).

    Returns:
        Dict with problem_id (the _id), db_id (serial PK), and message.
    """
    if not title or not title.strip():
        raise ValueError("标题不能为空")

    difficulty = difficulty if difficulty in VALID_DIFFICULTIES else "Low"
    rule_type = rule_type if rule_type in VALID_RULE_TYPES else "ACM"
    languages = languages or DEFAULT_LANGUAGES
    samples = samples or []
    tags = tags or []

    problem_display_id = _id or generate_problem_id()

    # Handle test cases: write files and compute hash
    test_case_id = ""
    test_case_score = []

    if test_cases:
        # Write to a temp dir first, compute the MD5 from info file,
        # then rename to the MD5-named directory (QDUOJ convention).
        import tempfile
        import shutil as _shutil
        with tempfile.TemporaryDirectory(prefix="tc_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            tc_id, test_case_score = write_test_case_files(tmp_path, test_cases)
            # tc_id is the MD5 hash of the info file
            final_dir = TEST_CASE_DIR / tc_id
            if not final_dir.exists():
                _shutil.copytree(tmp_path, final_dir)
                logger.info("Created test case dir: %s", final_dir)
            test_case_id = tc_id

    # Build SQL values
    now = datetime.now(timezone.utc)

    # Insert into public.problem
    # Note: asyncpg does not support ::jsonb cast syntax in parameterized queries.
    # Use CAST(... AS jsonb) instead.
    # Note: QDUOJ column names: create_time (not created_at), last_update_time
    # Note: Several NOT NULL columns need defaults: template, statistic_info, etc.
    insert_sql = text("""
        INSERT INTO problem (
            _id, title, description, input_description, output_description,
            samples, hint, source, difficulty, rule_type,
            time_limit, memory_limit, languages, template,
            test_case_id, test_case_score,
            visible, is_public, created_by_id, create_time, last_update_time,
            contest_id, spj, spj_compile_ok, io_mode, total_score,
            statistic_info, submission_number, accepted_number, share_submission
        ) VALUES (
            :_id, :title, :description, :input_description, :output_description,
            CAST(:samples AS jsonb), :hint, :source, :difficulty, :rule_type,
            :time_limit, :memory_limit, CAST(:languages AS jsonb), CAST(:template AS jsonb),
            :test_case_id, CAST(:test_case_score AS jsonb),
            :visible, :is_public, :created_by_id, :create_time, :last_update_time,
            NULL, false, false, CAST(:io_mode AS jsonb), :total_score,
            CAST(:statistic_info AS jsonb), 0, 0, false
        ) RETURNING id, _id
    """)

    result = await session.execute(insert_sql, {
        "_id": problem_display_id,
        "title": title.strip(),
        "description": description,
        "input_description": input_description,
        "output_description": output_description,
        "samples": json.dumps(samples, ensure_ascii=False),
        "hint": hint,
        "source": source,
        "difficulty": difficulty,
        "rule_type": rule_type,
        "time_limit": time_limit,
        "memory_limit": memory_limit,
        "languages": json.dumps(languages, ensure_ascii=False),
        "template": json.dumps({}, ensure_ascii=False),
        "test_case_id": test_case_id or problem_display_id,
        "test_case_score": json.dumps(test_case_score, ensure_ascii=False) if test_case_score else "[]",
        "visible": visible,
        "is_public": visible,
        "created_by_id": created_by_id,
        "create_time": now,
        "last_update_time": now,
        "io_mode": '{"io_mode":"Standard I/O"}',
        "total_score": sum(tc.get("score", 0) for tc in (test_cases or [])) or 100,
        "statistic_info": json.dumps({}, ensure_ascii=False),
    })
    row = result.fetchone()
    await session.flush()

    db_id = row[0]
    returned_id = row[1]

    # Handle tags: link problem → problem_tag via problem_tags junction table
    if tags:
        await _link_tags(session, db_id, tags)

    await session.commit()

    logger.info(
        "Created problem id=%s _id=%s title='%s' visible=%s",
        db_id, returned_id, title.strip(), visible,
    )

    return {
        "problem_id": returned_id,
        "db_id": db_id,
        "message": "题目创建成功",
    }


async def _link_tags(session: AsyncSession, problem_db_id: int, tag_names: list[str]) -> None:
    """Link a problem to tags by name. Creates tag entries if they don't exist."""
    for tag_name in tag_names:
        tag_name = tag_name.strip()
        if not tag_name:
            continue

        # Find or create tag in problem_tag table
        find_tag_sql = text("SELECT id FROM problem_tag WHERE name = :name")
        result = await session.execute(find_tag_sql, {"name": tag_name})
        tag_row = result.fetchone()

        if tag_row is None:
            insert_tag_sql = text(
                "INSERT INTO problem_tag (name) VALUES (:name) RETURNING id"
            )
            result = await session.execute(insert_tag_sql, {"name": tag_name})
            tag_row = result.fetchone()
            await session.flush()

        tag_id = tag_row[0]

        # Link in problem_tags junction table
        link_sql = text(
            "INSERT INTO problem_tags (problem_id, problemtag_id) VALUES (:pid, :tid) "
            "ON CONFLICT DO NOTHING"
        )
        await session.execute(link_sql, {"pid": problem_db_id, "tid": tag_id})

    await session.flush()


async def check_problem_exists(session: AsyncSession, title: str) -> dict | None:
    """Check if a problem with the given title already exists.

    Returns the matching problem row or None.
    """
    sql = text("SELECT id, _id, title FROM problem WHERE title = :title LIMIT 1")
    result = await session.execute(sql, {"title": title.strip()})
    row = result.fetchone()
    if row:
        return {"id": row[0], "_id": row[1], "title": row[2]}
    return None


async def get_tag_list(session: AsyncSession) -> list[dict]:
    """Get all tags from problem_tag table."""
    sql = text("SELECT id, name FROM problem_tag ORDER BY name")
    result = await session.execute(sql)
    return [{"id": row[0], "name": row[1]} for row in result.fetchall()]