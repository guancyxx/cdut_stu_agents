"""
POST /api/submit — accept code submissions and return judging results.

This is the replacement for QDUOJ's judge server flow.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.database import async_session
from app.models.submission import Submission
from app.services.judge_service import SandboxClient, judge_submission

logger = logging.getLogger("ai-agent-lite")

router = APIRouter(prefix="/api", tags=["submission"])


# ── request / response models ─────────────────────────────────────────
class SubmitRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=65536)
    language: str = Field(..., pattern=r"^(c|cpp|python3|java)$")
    problem_id: str = Field(..., min_length=1, max_length=64)
    user_id: str = Field(default="anonymous", max_length=64)


class TestCaseResultItem(BaseModel):
    case_index: int
    verdict: str
    time_sec: float = 0.0
    max_rss_kb: int = 0
    stdout: str = ""
    expected: str = ""
    stderr: str = ""


class SubmitResponse(BaseModel):
    submission_id: str
    verdict: str
    compile_error: str = ""
    test_case_results: list[dict] = []
    total_time_sec: float = 0.0
    max_rss_kb: int = 0


# ── endpoint ──────────────────────────────────────────────────────────

@router.post("/submit", response_model=SubmitResponse)
async def submit_code(req: SubmitRequest):
    """
    Submit code for judging.

    - Compiles and runs code against all test cases of the problem
    - Stores submission record in PostgreSQL
    - Returns verdict and per-test-case results
    """
    sandbox = SandboxClient()

    # Check sandbox health first
    if not await sandbox.health():
        raise HTTPException(503, "Sandbox service is unavailable")

    # Run the judge
    result = await judge_submission(
        code=req.code,
        language=req.language,
        problem_id=req.problem_id,
        sandbox=sandbox,
        user_id=req.user_id,
    )

    # Persist submission record
    submission_id = None
    try:
        async with async_session() as session:
            from app.models.submission import Submission
            sub = Submission(
                problem_id=req.problem_id,
                user_id=req.user_id,
                language=req.language,
                code=req.code,
                verdict=result.verdict,
                time_sec=result.total_time_sec,
                memory_kb=result.max_rss_kb,
                test_case_results=result.test_case_results,
                compile_error=result.compile_error,
            )
            session.add(sub)
            await session.commit()
            submission_id = str(sub.id)
    except Exception as exc:
        logger.error("Failed to persist submission: %s", exc)
        # Still return the result even if persistence fails

    return SubmitResponse(
        submission_id=submission_id or "unknown",
        verdict=result.verdict,
        compile_error=result.compile_error,
        test_case_results=result.test_case_results,
        total_time_sec=result.total_time_sec,
        max_rss_kb=result.max_rss_kb,
    )
