"""
Judge service for CDUT OJ — orchestrates compilation and execution.

Replaces QDUOJ's oj-judge with direct isolate sandbox integration.

Architecture:
  ai-agent-lite (this code)
    → HTTP POST to cdut-sandbox:8899/run
    → isolate sandbox compiles + executes
    → compare stdout against expected output
    → return verdict

Supports:
  - Standard comparison (exact match, ignoring trailing whitespace)
  - Special Judge (SPJ) via external Python scripts
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings


JAVA_MEMORY_FLOOR_KB = 1024 * 1024
MARKER_BLOCKS = ("PREPEND", "TEMPLATE", "APPEND")


# ── sandbox API client ────────────────────────────────────────────────
class SandboxClient:
    """Async HTTP client for the cdut-sandbox API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.judge_sandbox_url
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def run(
        self,
        code: str,
        language: str,
        input_data: str = "",
        time_limit: float = 2.0,
        memory_limit_kb: int = 262144,
    ) -> dict:
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/run",
            json={
                "code": code,
                "language": language,
                "input_data": input_data,
                "time_limit": time_limit,
                "memory_limit_kb": memory_limit_kb,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def health(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False


# ── data structures ───────────────────────────────────────────────────
class Verdict:
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    MLE = "MLE"
    RE = "RE"
    CE = "CE"
    SE = "SE"


@dataclass
class TestCaseResult:
    """Result for a single test case."""
    case_index: int  # 1-based
    verdict: str
    time_sec: float = 0.0
    max_rss_kb: int = 0
    stdout: str = ""
    expected: str = ""
    stderr: str = ""


@dataclass
class JudgeResult:
    """Full judging result for a submission."""
    verdict: str
    compile_error: str = ""
    test_case_results: list[dict] = field(default_factory=list)
    total_time_sec: float = 0.0
    max_rss_kb: int = 0


# ── database helpers ──────────────────────────────────────────────────

async def _get_problem_info(problem_id: str) -> Optional[dict]:
    """Fetch problem metadata from cdut-postgres."""
    from sqlalchemy import text
    from app.database import async_session

    async with async_session() as session:
        result = await session.execute(
            text("""
                SELECT _id, test_case_id, time_limit, memory_limit,
                       spj, spj_code, spj_language, spj_version
                FROM problem
                WHERE _id = :pid OR CAST(id AS TEXT) = :pid
            """),
            {"pid": problem_id},
        )
        row = result.fetchone()
        if not row:
            return None
        return {
            "_id": row[0],
            "test_case_id": row[1],
            "time_limit": row[2] or 1000,
            "memory_limit": row[3] or 256,
            "spj": row[4] or False,
            "spj_code": row[5],
            "spj_language": row[6],
            "spj_version": row[7],
        }


def _get_test_case_path(test_case_id: str) -> Path:
    """Get the path to test case files for a problem."""
    return Path("/data/test_cases") / test_case_id


# ── output comparison ─────────────────────────────────────────────────

def _normalize(output: str) -> str:
    """Normalize output for comparison: strip trailing whitespace per line."""
    lines = output.rstrip("\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)


def _compare_output(stdout: str, expected: str) -> bool:
    """Compare program output with expected output."""
    return _normalize(stdout) == _normalize(expected)


def _extract_marker_block(code: str, block_name: str) -> Optional[str]:
    """Extract a marker block body from wrapped template source."""
    begin_marker = f"//{block_name} BEGIN"
    end_marker = f"//{block_name} END"

    begin_index = code.find(begin_marker)
    if begin_index < 0:
        return None

    body_start = begin_index + len(begin_marker)
    end_index = code.find(end_marker, body_start)
    if end_index < 0:
        return None

    return code[body_start:end_index].strip("\n ")


def _sanitize_submission_code(code: str, language: str) -> str:
    """
    Rebuild executable source from marker-wrapped templates when present.

    Marker format:
      //PREPEND BEGIN ... //PREPEND END
      //TEMPLATE BEGIN ... //TEMPLATE END
      //APPEND BEGIN ... //APPEND END
    """
    if "//TEMPLATE BEGIN" not in code or "//TEMPLATE END" not in code:
        return code

    extracted: list[str] = []
    for block in MARKER_BLOCKS:
        body = _extract_marker_block(code, block)
        if body is None:
            return code
        if body.strip():
            extracted.append(body)

    if not extracted:
        return code

    if language not in {"python3", "java"}:
        return code

    return "\n\n".join(extracted).strip() + "\n"


def _effective_memory_limit_kb(language: str, configured_limit_kb: int) -> int:
    """Apply language-specific sandbox memory policy."""
    if language == "java":
        return max(configured_limit_kb, JAVA_MEMORY_FLOOR_KB)
    return configured_limit_kb


# ── SPJ execution ─────────────────────────────────────────────────────

async def _run_spj(
    sandbox: SandboxClient,
    input_path: Path,
    output_path: Path,
    spj_code: str,
    spj_language: str,
) -> bool:
    """
    Run Special Judge script.

    The SPJ receives:
      stdin:  input_file_content + "\n" + output_file_content
    Returns True if accepted.
    """
    input_data = input_path.read_text(encoding="utf-8", errors="replace")
    output_data = output_path.read_text(encoding="utf-8", errors="replace")
    spj_input = f"{input_data}\n{output_data}"

    result = await sandbox.run(
        code=spj_code,
        language=spj_language,
        input_data=spj_input,
        time_limit=5.0,
        memory_limit_kb=262144,
    )

    # SPJ returns 0 for AC, non-zero for WA
    return result.get("exit_code", 1) == 0 and result.get("verdict") == "AC"


# ── judge orchestration ───────────────────────────────────────────────

async def judge_submission(
    code: str,
    language: str,
    problem_id: str,
    sandbox: Optional[SandboxClient] = None,
    user_id: str = "anonymous",
) -> JudgeResult:
    """
    Judge a code submission against all test cases of a problem.

    Args:
        code: Source code
        language: One of 'c', 'cpp', 'python3', 'java'
        problem_id: Problem _id from the database
        sandbox: SandboxClient instance (created if None)

    Returns:
        JudgeResult with final verdict and per-test-case details
    """
    if sandbox is None:
        sandbox = SandboxClient()

    code_to_judge = _sanitize_submission_code(code, language)

    # 1. Fetch problem info
    problem = await _get_problem_info(problem_id)
    if not problem:
        return JudgeResult(verdict=Verdict.SE, compile_error=f"Problem not found: {problem_id}")

    test_case_id = problem["test_case_id"]
    if not test_case_id:
        return JudgeResult(verdict=Verdict.SE, compile_error=f"No test cases for problem: {problem_id}")

    test_case_dir = _get_test_case_path(test_case_id)
    if not test_case_dir.is_dir():
        return JudgeResult(
            verdict=Verdict.SE,
            compile_error=f"Test case directory not found: {test_case_dir}",
        )

    # 2. Discover test cases (pairs of .in / .out or .in / .ans)
    input_files = sorted(test_case_dir.glob("*.in"))
    if not input_files:
        return JudgeResult(
            verdict=Verdict.SE,
            compile_error=f"No .in files in test case directory: {test_case_dir}",
        )

    # 3. Compile once (outside sandbox — the /run endpoint handles this)
    # We do a dry-run to detect CE early.
    time_limit_ms = problem["time_limit"]
    time_limit_sec = max(1.0, time_limit_ms / 1000.0) if time_limit_ms else 2.0
    memory_limit_mb = problem["memory_limit"] or 256
    memory_limit_kb = memory_limit_mb * 1024
    effective_memory_limit_kb = _effective_memory_limit_kb(language, memory_limit_kb)

    # 4. Run against each test case
    test_case_results: list[dict] = []
    final_verdict = Verdict.AC
    total_time = 0.0
    max_rss = 0

    for idx, input_file in enumerate(input_files, start=1):
        # Find matching output file (.out or .ans)
        expected_file = input_file.with_suffix(".out")
        if not expected_file.is_file():
            expected_file = input_file.with_suffix(".ans")
        if not expected_file.is_file():
            test_case_results.append({
                "case_index": idx,
                "verdict": Verdict.SE,
                "message": f"No expected output for {input_file.name}",
            })
            if final_verdict == Verdict.AC:
                final_verdict = Verdict.SE
            continue

        # Read input
        input_data = input_file.read_text(encoding="utf-8", errors="replace")
        expected_data = expected_file.read_text(encoding="utf-8", errors="replace")

        # Call sandbox
        try:
            result = await sandbox.run(
                code=code_to_judge,
                language=language,
                input_data=input_data,
                time_limit=time_limit_sec,
                memory_limit_kb=effective_memory_limit_kb,
            )
        except Exception as exc:
            test_case_results.append({
                "case_index": idx,
                "verdict": Verdict.SE,
                "message": f"Sandbox error: {exc}",
            })
            if final_verdict == Verdict.AC:
                final_verdict = Verdict.SE
            continue

        verdict = result.get("verdict", Verdict.SE)
        compile_success = result.get("compile_success", True)

        if not compile_success:
            # CE — compilation failed, stop here
            return JudgeResult(
                verdict=Verdict.CE,
                compile_error=result.get("compile_stderr", "Compilation failed"),
            )

        time_sec = result.get("time_sec", 0)
        rss = result.get("max_rss_kb", 0)
        stdout = result.get("stdout", "")

        total_time += time_sec
        max_rss = max(max_rss, rss)

        tc_result = {
            "case_index": idx,
            "verdict": verdict,
            "time_sec": time_sec,
            "max_rss_kb": rss,
            "stdout": stdout[:1024],
            "expected": expected_data[:1024],
            "stderr": result.get("stderr", "")[:512],
        }

        # If sandbox already returned non-AC, use that verdict
        if verdict != Verdict.AC:
            tc_result["verdict"] = verdict
            test_case_results.append(tc_result)
            if final_verdict == Verdict.AC:
                final_verdict = verdict
            continue

        # Compare output
        if problem.get("spj") and problem.get("spj_code"):
            # SPJ mode
            try:
                accepted = await _run_spj(
                    sandbox, input_file,
                    test_case_dir / f"{input_file.stem}.out_tmp",
                    problem["spj_code"],
                    problem.get("spj_language", "python3"),
                )
                if not accepted:
                    tc_result["verdict"] = Verdict.WA
                    if final_verdict == Verdict.AC:
                        final_verdict = Verdict.WA
            except Exception:
                tc_result["verdict"] = Verdict.SE
                if final_verdict == Verdict.AC:
                    final_verdict = Verdict.SE
        else:
            if not _compare_output(stdout, expected_data):
                tc_result["verdict"] = Verdict.WA
                if final_verdict == Verdict.AC:
                    final_verdict = Verdict.WA

        test_case_results.append(tc_result)

    return JudgeResult(
        verdict=final_verdict,
        test_case_results=test_case_results,
        total_time_sec=total_time,
        max_rss_kb=max_rss,
    )
