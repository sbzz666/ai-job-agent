from pathlib import Path

from fastapi.testclient import TestClient

from app import api
from app.services.task_repository import TaskRepository
from app.services.workflow import JobAnalysisWorkflow


def test_end_to_end_analysis_api(tmp_path: Path, monkeypatch) -> None:
    repository = TaskRepository(tmp_path / "api.db")
    monkeypatch.setattr(api, "repository", repository)
    monkeypatch.setattr(api, "workflow", JobAnalysisWorkflow(repository))
    client = TestClient(api.app)

    response = client.post(
        "/api/v1/analyses",
        files={"resume": ("resume.txt", "本科\n3 年 Python FastAPI 开发经验".encode("utf-8"))},
        data={"job_description": "本科，要求 3 年开发经验，熟悉 Python、FastAPI 和 Redis。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"]
    assert payload["matched_skills"] == ["Python", "FastAPI"]
    assert payload["missing_skills"] == ["Redis"]
    assert client.get(f"/api/v1/analyses/{payload['task_id']}").status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-request-id"]
