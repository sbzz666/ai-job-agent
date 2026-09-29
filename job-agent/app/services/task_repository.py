"""SQLite persistence for analysis history without storing resume text."""

from __future__ import annotations

from pathlib import Path
from contextlib import closing
import json
import re
import sqlite3
from uuid import uuid4

from app.models import MatchReport, TaskSummary


class TaskRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_tasks (
                        task_id TEXT PRIMARY KEY,
                        resume_name TEXT NOT NULL,
                        overall_score REAL NOT NULL,
                        report_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )

    def save(self, report: MatchReport) -> MatchReport:
        stored = report.model_copy(deep=True, update={"task_id": report.task_id or uuid4().hex})
        for item in stored.evidence:
            item.evidence = [_redact_personal_data(line) for line in item.evidence]
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO analysis_tasks VALUES (?, ?, ?, ?, ?)",
                    (
                        stored.task_id,
                        stored.resume_name,
                        stored.overall_score,
                        stored.model_dump_json(),
                        stored.created_at.isoformat(),
                    ),
                )
        return stored

    def list_recent(self, limit: int = 20) -> list[TaskSummary]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT task_id, resume_name, overall_score, created_at
                   FROM analysis_tasks ORDER BY created_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [TaskSummary.model_validate(dict(row)) for row in rows]

    def get(self, task_id: str) -> MatchReport | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT report_json FROM analysis_tasks WHERE task_id = ?", (task_id,)
            ).fetchone()
        return MatchReport.model_validate(json.loads(row["report_json"])) if row else None


def _redact_personal_data(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[邮箱已隐藏]", text)
    text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已隐藏]", text)
    text = re.sub(
        r"(?:微信|WeChat|wechat)\s*[:：]?\s*[A-Za-z][-_A-Za-z0-9]{5,19}",
        "微信：[已隐藏]",
        text,
    )
    return text


class TransientTaskRepository:
    """Assign task IDs without persisting cross-user data."""

    def save(self, report: MatchReport) -> MatchReport:
        return report.model_copy(update={"task_id": report.task_id or uuid4().hex})
