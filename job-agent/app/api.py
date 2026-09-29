"""FastAPI entry point for the deployable job assistant MVP."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.models import MatchReport, TaskSummary
from app.services.resume_parser import ResumeParseError, SUPPORTED_SUFFIXES
from app.services.task_repository import TaskRepository
from app.services.workflow import JobAnalysisWorkflow


BASE_DIR = Path(__file__).resolve().parents[1]
repository = TaskRepository(BASE_DIR / "data" / "tasks.db")
workflow = JobAnalysisWorkflow(repository)
IS_PRODUCTION = os.getenv("APP_ENV", "development").casefold() == "production"
ENABLE_HISTORY_API = os.getenv("ENABLE_HISTORY_API", "false").casefold() == "true"
app = FastAPI(
    title="AI 求职助手",
    version="0.3.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", uuid4().hex)[:64]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/analyses", response_model=MatchReport)
async def create_analysis(
    resume: UploadFile = File(...),
    job_description: str = Form(..., min_length=10, max_length=20_000),
) -> MatchReport:
    safe_name = Path(resume.filename or "resume").name
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(415, "仅支持 TXT、DOCX、PDF。")

    content = await resume.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "文件不能超过 10 MB。")

    try:
        with TemporaryDirectory(prefix="job-agent-") as temp_dir:
            path = Path(temp_dir) / safe_name
            path.write_bytes(content)
            return workflow.run(path, job_description)
    except (ResumeParseError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/v1/analyses", response_model=list[TaskSummary])
def list_analyses() -> list[TaskSummary]:
    if IS_PRODUCTION and not ENABLE_HISTORY_API:
        raise HTTPException(404, "接口不存在。")
    return repository.list_recent()


@app.get("/api/v1/analyses/{task_id}", response_model=MatchReport)
def get_analysis(task_id: str) -> MatchReport:
    if IS_PRODUCTION and not ENABLE_HISTORY_API:
        raise HTTPException(404, "接口不存在。")
    report = repository.get(task_id)
    if report is None:
        raise HTTPException(404, "任务不存在。")
    return report
