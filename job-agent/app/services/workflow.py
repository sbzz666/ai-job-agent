"""Single-agent orchestration: parse, match, validate and record."""

from __future__ import annotations

from pathlib import Path

from app.models import MatchReport
from app.services.job_matcher import analyze_match
from app.services.resume_parser import ParsedResume, parse_resume
from app.services.task_repository import TaskRepository


class JobAnalysisWorkflow:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def run(self, resume_path: str | Path, job_description: str) -> MatchReport:
        parsed = parse_resume(resume_path)
        return self.run_parsed(parsed, job_description)

    def run_parsed(self, parsed: ParsedResume, job_description: str) -> MatchReport:
        report = analyze_match(parsed.source_name, parsed.text, job_description)
        return self.repository.save(report)
