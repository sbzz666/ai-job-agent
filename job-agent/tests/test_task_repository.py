from pathlib import Path

from app.services.job_matcher import analyze_match
from app.services.task_repository import TaskRepository


def test_save_and_read_analysis_without_resume_body(tmp_path: Path) -> None:
    database = tmp_path / "tasks.db"
    repository = TaskRepository(database)
    report = analyze_match(
        "resume.txt",
        "内部自我介绍，不是岗位证据\nPython 项目，邮箱 user@example.com，手机 13800138000",
        "需要 Python",
    )

    saved = repository.save(report)
    loaded = repository.get(saved.task_id or "")

    assert loaded == saved
    assert repository.list_recent()[0].task_id == saved.task_id
    database_text = database.read_bytes().decode("utf-8", errors="ignore")
    assert "内部自我介绍" not in database_text
    assert "user@example.com" not in database_text
    assert "13800138000" not in database_text
    assert loaded.evidence[0].evidence == ["Python 项目，邮箱 [邮箱已隐藏]，手机 [手机号已隐藏]"]
