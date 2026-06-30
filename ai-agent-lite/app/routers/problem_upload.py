"""REST API endpoints for admin problem upload (single + batch).

All operations go through ai-agent-lite → direct PostgreSQL DB write.
No legacy OJ Admin API calls.

Endpoints:
  POST /admin/problems/create          — Single problem creation
  POST /admin/problems/upload/batch    — Batch import (FPS XML / Hydro ZIP)
  GET  /admin/problems/import/status   — Poll batch import progress
  GET  /admin/problems/tags            — List available tags
"""

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from app.celery_app import celery_app
from app.database import async_session
from app.services.problem_import import detect_format
from app.services.problem_service import create_problem, get_tag_list, update_problem
from app.tasks.batch_import import batch_import_problems, get_import_progress

logger = logging.getLogger("ai-agent-lite.problem_upload_api")

router = APIRouter(prefix="/admin/problems", tags=["admin-problem-upload"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SampleItem(BaseModel):
    input: str = ""
    output: str = ""


class ProblemCreateRequest(BaseModel):
    """Request body for single problem creation."""
    title: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    input_description: str = ""
    output_description: str = ""
    samples: list[SampleItem] = []
    hint: str = ""
    source: str = ""
    difficulty: str = "Low"
    rule_type: str = "ACM"
    time_limit: int = Field(default=1000, ge=100, le=60000)
    memory_limit: int = Field(default=256, ge=16, le=1024)
    languages: list[str] = ["C", "C++", "Java", "Python3"]
    visible: bool = False
    tags: list[str] = []
    test_cases: list[SampleItem] = []
    template: dict = {}
    spj: bool = False
    spj_language: str = ""
    spj_code: str = ""


class ProblemCreateResponse(BaseModel):
    success: bool
    problem_id: str
    db_id: int
    message: str


class ProblemUpdateRequest(BaseModel):
    """Request body for problem update."""
    title: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    input_description: str = ""
    output_description: str = ""
    hint: str = ""
    source: str = ""
    difficulty: str = "Low"
    time_limit: int = Field(default=1000, ge=100, le=60000)
    memory_limit: int = Field(default=256, ge=16, le=1024)
    visible: bool = False
    tags: list[str] = []


class ProblemUpdateResponse(BaseModel):
    success: bool
    problem_id: str
    db_id: int
    message: str


class BatchImportResponse(BaseModel):
    task_id: str
    status: str
    total: int
    message: str


class ImportStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending" | "running" | "completed" | "failed"
    total: int
    imported: int
    skipped: int
    failed: int
    failed_details: list[dict] = []


# ---------------------------------------------------------------------------
# Upload directory for batch files
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/data/problems"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create", response_model=ProblemCreateResponse)
async def create_single_problem(req: ProblemCreateRequest, request: Request):
    """Create a single problem via direct DB write.

    If test_cases are provided, writes test case files to the shared volume.
    """
    from app.utils.auth_helpers import require_admin_username
    await require_admin_username(request)
    # Convert pydantic models to plain dicts
    samples = [{"input": s.input, "output": s.output} for s in req.samples]
    test_cases = [{"input": tc.input, "output": tc.output} for tc in req.test_cases]

    async with async_session() as session:
        try:
            result = await create_problem(
                session,
                title=req.title,
                description=req.description,
                input_description=req.input_description,
                output_description=req.output_description,
                samples=samples,
                hint=req.hint,
                source=req.source,
                difficulty=req.difficulty,
                rule_type=req.rule_type,
                time_limit=req.time_limit,
                memory_limit=req.memory_limit,
                languages=req.languages,
                template=req.template,
                visible=req.visible,
                tags=req.tags,
                test_cases=test_cases if test_cases else None,
                spj=req.spj,
                spj_language=req.spj_language,
                spj_code=req.spj_code,
                created_by_id=1,
            )
            return ProblemCreateResponse(
                success=True,
                problem_id=result["problem_id"],
                db_id=result["db_id"],
                message=result["message"],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to create problem: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"创建题目失败: {str(e)}")


@router.put("/{problem_id}", response_model=ProblemUpdateResponse)
async def update_single_problem(problem_id: str, req: ProblemUpdateRequest, request: Request):
    """Update a problem by display id or numeric id."""
    from app.utils.auth_helpers import require_admin_username

    await require_admin_username(request)

    async with async_session() as session:
        try:
            result = await update_problem(
                session,
                problem_id=problem_id,
                title=req.title,
                description=req.description,
                input_description=req.input_description,
                output_description=req.output_description,
                hint=req.hint,
                source=req.source,
                difficulty=req.difficulty,
                time_limit=req.time_limit,
                memory_limit=req.memory_limit,
                visible=req.visible,
                tags=req.tags,
            )
            return ProblemUpdateResponse(
                success=True,
                problem_id=result["problem_id"],
                db_id=result["db_id"],
                message=result["message"],
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("Failed to update problem: %s", e, exc_info=True)
            raise HTTPException(status_code=500, detail=f"更新题目失败: {str(e)}")


@router.post("/upload/batch", response_model=BatchImportResponse)
async def upload_batch(
    request: Request,
    file: UploadFile = File(...),
    format: str = Form("auto"),
    tags: str = Form(""),
    difficulty: str = Form(""),
    visible: bool = Form(False),
):
    """Batch import problems from FPS XML or Hydro ZIP file.

    The file is saved to a shared volume, then a Celery task is dispatched
    to process it asynchronously. The caller polls the status endpoint.
    """
    from app.utils.auth_helpers import require_admin_username
    await require_admin_username(request)
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")

    # Detect format
    try:
        fmt = format if format in ("fps", "hydro") else detect_format(file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save uploaded file to disk
    file_id = uuid.uuid4().hex[:12]
    suffix = ".xml" if fmt == "fps" else ".zip"
    save_path = UPLOAD_DIR / f"import_{file_id}{suffix}"

    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    logger.info("Saved batch upload file: %s (%d bytes, format=%s)", save_path, len(content), fmt)

    # Parse extra tags
    extra_tags = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    # Dispatch Celery task
    difficulty_override = difficulty if difficulty in ("Low", "Mid", "High") else None

    task = batch_import_problems.apply_async(
        kwargs={
            "file_path": str(save_path),
            "fmt": fmt,
            "extra_tags": extra_tags,
            "difficulty_override": difficulty_override,
            "visible": visible,
        },
        queue="audit",
    )

    logger.info("Dispatched batch import task_id=%s file=%s", task.id, save_path)

    return BatchImportResponse(
        task_id=task.id,
        status="pending",
        total=0,
        message="文件已接收，正在处理...",
    )


@router.get("/import/status/{task_id}", response_model=ImportStatusResponse)
async def get_import_status(task_id: str, request: Request):
    """Poll the status of a batch import task."""
    from app.utils.auth_helpers import require_admin_username
    await require_admin_username(request)
    progress = get_import_progress(task_id)

    if progress is None:
        # Check if the Celery task itself is still pending/running
        result = celery_app.AsyncResult(task_id)
        if result.status == "PENDING":
            return ImportStatusResponse(
                task_id=task_id,
                status="pending",
                total=0,
                imported=0,
                skipped=0,
                failed=0,
            )
        elif result.status == "FAILURE":
            return ImportStatusResponse(
                task_id=task_id,
                status="failed",
                total=0,
                imported=0,
                skipped=0,
                failed=1,
                failed_details=[{"title": "N/A", "reason": str(result.result)}],
            )
        # Task might have completed but progress key expired
        if result.status == "SUCCESS" and result.result:
            res = result.result if isinstance(result.result, dict) else {}
            return ImportStatusResponse(
                task_id=task_id,
                status="completed",
                total=res.get("total", 0),
                imported=res.get("imported", 0),
                skipped=res.get("skipped", 0),
                failed=res.get("failed", 0),
                failed_details=res.get("failed_details", []),
            )
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return ImportStatusResponse(
        task_id=task_id,
        status=progress.get("status", "unknown"),
        total=progress.get("total", 0),
        imported=progress.get("imported", 0),
        skipped=progress.get("skipped", 0),
        failed=progress.get("failed", 0),
        failed_details=progress.get("failed_details", []),
    )


@router.get("/tags")
async def list_tags(request: Request):
    """List all available problem tags from the database."""
    from app.utils.auth_helpers import require_admin_username
    await require_admin_username(request)
    async with async_session() as session:
        tags = await get_tag_list(session)
        return {"tags": tags}
