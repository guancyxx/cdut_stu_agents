"""
Lightweight HTTP API server for the isolate sandbox.

Wraps sandbox.py functions as REST endpoints so ai-agent-lite
can call them from its own container.

Endpoints:
  POST /compile  — compile source code
  POST /execute  — run compiled code in sandbox
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sandbox import (
    Language,
    Verdict,
    compile_code,
    execute,
    _write_temp,
    _extract_java_class,
    LANG_META,
)

app = FastAPI(title="cdut-sandbox-api", version="0.1.0")


# ── request / response models ─────────────────────────────────────────
class CompileRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=65536)
    language: str = Field(..., pattern=r"^(c|cpp|python3|java)$")


class CompileResponse(BaseModel):
    success: bool
    language: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    artifact_token: str | None = None  # opaque token to reference artifact


class ExecuteRequest(BaseModel):
    artifact_token: str = Field(...)
    language: str = Field(..., pattern=r"^(c|cpp|python3|java)$")
    input_data: str = ""
    time_limit: float = 2.0
    memory_limit_kb: int = 262144
    processes_limit: int = 100


class ExecuteResponse(BaseModel):
    verdict: str
    time_sec: float = 0.0
    time_wall_sec: float = 0.0
    max_rss_kb: int = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""


# ── in-memory artifact store ──────────────────────────────────────────
# Maps token -> (artifact_path, language)
_artifacts: dict[str, tuple[str, str]] = {}


# ── routes ────────────────────────────────────────────────────────────

@app.post("/compile", response_model=CompileResponse)
async def api_compile(req: CompileRequest):
    """Compile source code, return an artifact token for execution."""
    try:
        lang = Language(req.language)
    except ValueError:
        raise HTTPException(400, f"Unsupported language: {req.language}")

    result = await compile_code(req.code, lang)

    token = None
    if result.success and result.artifact_path:
        token = uuid.uuid4().hex[:12]
        _artifacts[token] = (result.artifact_path, req.language)

    return CompileResponse(
        success=result.success,
        language=result.language.value,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
        artifact_token=token,
    )


@app.post("/execute", response_model=ExecuteResponse)
async def api_execute(req: ExecuteRequest):
    """Execute a compiled artifact inside the sandbox."""
    artifact_entry = _artifacts.get(req.artifact_token)
    if not artifact_entry:
        raise HTTPException(404, f"Artifact token not found: {req.artifact_token}")

    artifact_path, language_str = artifact_entry

    try:
        lang = Language(language_str)
    except ValueError:
        raise HTTPException(400, f"Unsupported language: {language_str}")

    # For Python3, the artifact_path may be None (compile_code returns success with None)
    # In that case, we need the original code — but we stored the token at compile time
    # For Python3 we need to write temp file from stored code.
    # Workaround: Python3 compile always returns artifact_path=None, so the token
    # was never stored. The caller should use /run endpoint instead.
    if language_str == "python3" and artifact_path is None:
        raise HTTPException(400, "Python3 requires /run endpoint, not /compile + /execute")

    result = await execute(
        artifact_path=artifact_path,
        language=lang,
        input_data=req.input_data,
        time_limit=req.time_limit,
        memory_limit_kb=req.memory_limit_kb,
        processes_limit=req.processes_limit,
    )

    return ExecuteResponse(
        verdict=result.verdict.value,
        time_sec=result.time_sec,
        time_wall_sec=result.time_wall_sec,
        max_rss_kb=result.max_rss_kb,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        message=result.message,
    )


class RunRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=65536)
    language: str = Field(..., pattern=r"^(c|cpp|python3|java)$")
    input_data: str = ""
    time_limit: float = 2.0
    memory_limit_kb: int = 262144


class RunResponse(BaseModel):
    compile_success: bool
    compile_stdout: str = ""
    compile_stderr: str = ""
    verdict: str = "SE"
    time_sec: float = 0.0
    time_wall_sec: float = 0.0
    max_rss_kb: int = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""


@app.post("/run", response_model=RunResponse)
async def api_run(req: RunRequest):
    """Compile + execute in one call. Preferred for Python3 and simple cases."""
    try:
        lang = Language(req.language)
    except ValueError:
        raise HTTPException(400, f"Unsupported language: {req.language}")

    compile_result = await compile_code(req.code, lang)

    if not compile_result.success:
        return RunResponse(
            compile_success=False,
            compile_stdout=compile_result.stdout,
            compile_stderr=compile_result.stderr,
            verdict=Verdict.CE.value,
            message="Compilation failed",
        )

    # Determine artifact path
    if lang == Language.PYTHON3:
        artifact_path = _write_temp(req.code, lang)
    else:
        artifact_path = compile_result.artifact_path

    if artifact_path is None:
        return RunResponse(
            compile_success=True,
            verdict=Verdict.SE.value,
            message="No artifact produced",
        )

    exec_result = await execute(
        artifact_path=artifact_path,
        language=lang,
        input_data=req.input_data,
        time_limit=req.time_limit,
        memory_limit_kb=req.memory_limit_kb,
    )

    return RunResponse(
        compile_success=True,
        compile_stdout=compile_result.stdout,
        compile_stderr=compile_result.stderr,
        verdict=exec_result.verdict.value,
        time_sec=exec_result.time_sec,
        time_wall_sec=exec_result.time_wall_sec,
        max_rss_kb=exec_result.max_rss_kb,
        exit_code=exec_result.exit_code,
        stdout=exec_result.stdout,
        stderr=exec_result.stderr,
        message=exec_result.message,
    )


@app.get("/health")
async def health():
    return {"status": "ok", "sandbox": "isolate-v2.5"}
