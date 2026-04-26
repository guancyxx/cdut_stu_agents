"""OJ test case content API — serves test case input/output for debugging.

This router allows the frontend to display per-test-case input, expected output,
and (when available) the user's actual output alongside submission results.

Uses direct PostgreSQL queries instead of the OJ admin HTTP API,
because QDUOJ's CSRF-protected login endpoint rejects programmatic requests.
"""
import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.config import settings

logger = logging.getLogger("ai-agent-lite")

router = APIRouter(prefix="/oj", tags=["oj-test-cases"])

# Path to test_case directory inside the container (volume-mounted from OJ backend)
TEST_CASE_DIR = os.getenv("OJ_TEST_CASE_DIR", "/data/test_case")


def _get_db_connection():
    """Get a direct psycopg2 connection to the OJ PostgreSQL database."""
    import psycopg2
    db_url = settings.db_url.replace("+asyncpg", "")
    return psycopg2.connect(db_url)


def _lookup_problem_by_display_id(display_id: str) -> Optional[dict]:
    """Look up problem by display _id (e.g. 'fps-e9c7') via direct DB query."""
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, test_case_id FROM problem WHERE _id = %s",
            (display_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {"id": row[0], "test_case_id": row[1] or ""}
        return None
    except Exception as exc:
        logger.warning("Failed to look up problem by display_id %s: %s", display_id, exc)
        return None


def _lookup_problem_by_numeric_id(numeric_id: int) -> Optional[dict]:
    """Look up problem by numeric id via direct DB query."""
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, _id, test_case_id FROM problem WHERE id = %s",
            (numeric_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {"id": row[0], "_id": row[1] or "", "test_case_id": row[2] or ""}
        return None
    except Exception as exc:
        logger.warning("Failed to look up problem by numeric_id %s: %s", numeric_id, exc)
        return None


def _fetch_submission_detail_db(submission_id: str) -> Optional[dict]:
    """Fetch submission detail from PostgreSQL directly.

    Returns a dict with 'info' field matching the OJ API response structure,
    or None if not found / not accessible.
    """
    try:
        conn = _get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT result, statistic_info, info FROM submission WHERE id = %s",
            (submission_id,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None

        result_code, statistic_info_raw, info_raw = row

        # Parse info field — it stores per-test-case data as JSON
        info = None
        if isinstance(info_raw, dict):
            info = info_raw
        elif isinstance(info_raw, str) and info_raw:
            try:
                info = json.loads(info_raw)
            except (json.JSONDecodeError, ValueError):
                pass

        # Parse statistic_info
        stat_info = None
        if isinstance(statistic_info_raw, dict):
            stat_info = statistic_info_raw
        elif isinstance(statistic_info_raw, str) and statistic_info_raw:
            try:
                stat_info = json.loads(statistic_info_raw)
            except (json.JSONDecodeError, ValueError):
                pass

        return {
            "result": result_code,
            "statistic_info": stat_info or {},
            "info": info or {},
        }
    except Exception as exc:
        logger.warning("Failed to fetch submission %s from DB: %s", submission_id, exc)
        return None


@router.get("/test_case_content")
async def get_test_case_content(
    problem_id: str = "",
    submission_id: str = "",
    problem__id: str = "",
):
    """Return test case input, expected output, and user output for debugging.

    Accepts either:
      - problem_id  (numeric OJ internal ID) to just get test case I/O
      - submission_id to also include the user's actual output per test case

    Returns:
      {
        "test_cases": [
          {
            "index": 1,
            "input": "...",
            "expected_output": "...",
            "actual_output": "..." | null,
            "status": 0,
            "cpu_time": 5,
            "memory": 8040448
          },
          ...
        ]
      }
    """
    # Resolve problem__id (display ID like "LQ1273") to internal problem_id if needed
    resolved_problem_id = problem_id
    test_case_id = ""

    if not resolved_problem_id and problem__id:
        # Look up by display _id via direct DB query
        problem_data = _lookup_problem_by_display_id(problem__id)
        if not problem_data:
            raise HTTPException(status_code=404, detail="Problem not found")
        resolved_problem_id = str(problem_data["id"])
        test_case_id = problem_data.get("test_case_id", "")

    if not resolved_problem_id:
        raise HTTPException(status_code=400, detail="problem_id or problem__id is required")

    # If we don't have test_case_id yet, look up by numeric ID
    if not test_case_id:
        problem_data = _lookup_problem_by_numeric_id(int(resolved_problem_id))
        if not problem_data:
            raise HTTPException(status_code=404, detail="Problem not found")
        test_case_id = problem_data.get("test_case_id", "")

    if not test_case_id:
        raise HTTPException(status_code=404, detail="Problem has no test cases")

    test_case_dir = os.path.join(TEST_CASE_DIR, test_case_id)
    if not os.path.isdir(test_case_dir):
        raise HTTPException(status_code=404, detail="Test case directory not found on disk")

    # Read the info file to get file name mapping
    info_path = os.path.join(test_case_dir, "info")
    if not os.path.isfile(info_path):
        raise HTTPException(status_code=404, detail="Test case info file not found")

    try:
        with open(info_path, "r", encoding="utf-8") as f:
            info_data = json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read test case info: {exc}")

    # Fetch submission detail from DB if submission_id is provided
    submission_detail = None
    if submission_id:
        submission_detail = _fetch_submission_detail_db(submission_id)

    # Build a map of test_case index -> user output from submission info
    user_outputs = {}
    if submission_detail and isinstance(submission_detail.get("info"), dict):
        info_obj = submission_detail["info"]
        tc_data = info_obj.get("data")
        if isinstance(tc_data, list):
            for tc in tc_data:
                tc_idx = str(tc.get("test_case", ""))
                if tc.get("output") is not None:
                    user_outputs[tc_idx] = tc["output"]

    # Build result
    test_case_map = info_data.get("test_cases", {})
    result_cases = []

    for idx_str, tc_info in sorted(test_case_map.items(), key=lambda x: int(x[0])):
        input_name = tc_info.get("input_name", "")
        output_name = tc_info.get("output_name", "")

        # Read input file
        input_content = ""
        if input_name:
            input_path = os.path.join(test_case_dir, input_name)
            try:
                with open(input_path, "r", encoding="utf-8", errors="backslashreplace") as f:
                    # Limit to 32KB per file to avoid huge responses
                    input_content = f.read(32768)
            except (IOError, OSError):
                input_content = f"[Error reading {input_name}]"

        # Read expected output file
        expected_output = ""
        if output_name:
            output_path = os.path.join(test_case_dir, output_name)
            try:
                with open(output_path, "r", encoding="utf-8", errors="backslashreplace") as f:
                    expected_output = f.read(32768)
            except (IOError, OSError):
                expected_output = f"[Error reading {output_name}]"

        # QDUOJ info file uses 1-based keys ("1", "2", "3"...), same as submission's test_case field.
        # No offset needed — idx_str matches directly.
        tc_index = int(idx_str)

        case_result = {
            "index": tc_index,
            "input": input_content,
            "expected_output": expected_output,
            "actual_output": user_outputs.get(idx_str, None),
        }

        # Include test case status/metrics from submission if available
        if submission_detail and isinstance(submission_detail.get("info"), dict):
            tc_data_list = submission_detail["info"].get("data", [])
            if isinstance(tc_data_list, list):
                matching_tc = next(
                    (tc for tc in tc_data_list if str(tc.get("test_case", "")) == idx_str),
                    None
                )
                if matching_tc:
                    case_result["status"] = matching_tc.get("result")
                    case_result["cpu_time"] = matching_tc.get("cpu_time")
                    case_result["memory"] = matching_tc.get("memory")
                    case_result["score"] = matching_tc.get("score")

        result_cases.append(case_result)

    return {"test_cases": result_cases}