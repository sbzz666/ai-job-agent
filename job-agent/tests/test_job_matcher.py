from app.services.job_matcher import analyze_match


def test_match_report_is_explainable() -> None:
    resume = """本科
    3 年 Python 后端开发经验
    项目：使用 Python、FastAPI 和 Docker 构建 RESTful 服务。"""
    jd = "本科及以上学历，3 年以上开发经验，熟悉 Python、FastAPI、Docker、Redis。"

    report = analyze_match("resume.txt", resume, jd)

    assert report.overall_score > 70
    assert report.matched_skills == ["Python", "FastAPI", "Docker"]
    assert report.missing_skills == ["Redis"]
    assert report.required_experience_years == 3
    assert report.detected_experience_years == 3
    assert any(item.requirement == "FastAPI" and item.evidence for item in report.evidence)
    assert any("Redis" in suggestion for suggestion in report.recommendations)


def test_never_claims_missing_skill_as_evidence() -> None:
    report = analyze_match("resume.txt", "Python 项目", "需要 Python 和 Kubernetes")

    kubernetes = next(item for item in report.evidence if item.requirement == "Kubernetes")
    assert not kubernetes.matched
    assert kubernetes.evidence == []
