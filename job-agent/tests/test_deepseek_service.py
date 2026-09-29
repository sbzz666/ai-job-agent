import json
from types import SimpleNamespace

from app.services.deepseek_service import DeepSeekCareerService
from app.services.job_matcher import analyze_match


class FakeResponses:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def create(self, **kwargs):
        return SimpleNamespace(output_text=json.dumps(self.payload, ensure_ascii=False))


class FakeClient:
    def __init__(self, payload: dict) -> None:
        self.responses = FakeResponses(payload)


def test_generate_guidance_and_fact_check() -> None:
    payload = {
        "resume_suggestions": ["补充 FastAPI 项目的量化结果"],
        "self_introduction": "我有 3 年 Python 和 Kubernetes 开发经验，负责后端接口。",
        "interview_questions": [
            {"question": "如何设计接口？", "evaluation_focus": "工程能力", "reference_answer": "使用 FastAPI。"}
        ],
    }
    service = DeepSeekCareerService(FakeClient(payload), model="test-model")
    resume = "本科，3 年 Python 开发经验，使用 FastAPI 构建接口。"
    report = analyze_match("resume.txt", resume, "需要 Python、FastAPI 和 Kubernetes")

    result = service.generate_guidance(resume, "需要 Python、FastAPI 和 Kubernetes", report)

    assert result.model == "test-model"
    assert not result.verified
    assert any("Kubernetes" in warning for warning in result.fact_check_warnings)


def test_grounded_question_answer() -> None:
    payload = {"answer": "候选人使用 FastAPI 开发接口。", "evidence": ["使用 FastAPI 构建接口。"], "refused": False}
    service = DeepSeekCareerService(FakeClient(payload), model="test-model")

    result = service.answer_question("做过什么后端项目？", "使用 FastAPI 构建接口。", "需要 Python")

    assert result.answer.startswith("候选人")
    assert not result.refused
