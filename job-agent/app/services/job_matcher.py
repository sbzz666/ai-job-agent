"""Deterministic and explainable resume-to-job matching baseline."""

from __future__ import annotations

import re

from app.models import MatchReport, RequirementEvidence, ScoreBreakdown


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "FastAPI": ("fastapi",),
    "Django": ("django",),
    "Flask": ("flask",),
    "SQL": ("sql",),
    "MySQL": ("mysql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "Redis": ("redis",),
    "Docker": ("docker", "容器化"),
    "Kubernetes": ("kubernetes", "k8s"),
    "Git": ("git",),
    "Linux": ("linux",),
    "REST API": ("rest api", "restful", "接口开发"),
    "OpenAI API": ("openai api", "responses api"),
    "RAG": ("rag", "检索增强生成"),
    "LangChain": ("langchain",),
    "ChromaDB": ("chromadb", "chroma"),
    "FAISS": ("faiss",),
    "LLM": ("llm", "大语言模型", "大模型"),
    "NLP": ("nlp", "自然语言处理"),
    "PyTorch": ("pytorch",),
    "TensorFlow": ("tensorflow",),
    "Pandas": ("pandas",),
    "NumPy": ("numpy",),
    "Java": ("java",),
    "Spring Boot": ("spring boot", "springboot"),
    "JavaScript": ("javascript",),
    "TypeScript": ("typescript",),
    "React": ("react",),
    "Vue": ("vue",),
    "AWS": ("aws",),
    "Azure": ("azure",),
}

EDUCATION_RANK = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}


def _contains_alias(text: str, aliases: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(alias.casefold() in lowered for alias in aliases)


def _extract_skills(text: str) -> list[str]:
    return [name for name, aliases in SKILL_ALIASES.items() if _contains_alias(text, aliases)]


def _extract_required_years(text: str) -> int | None:
    matches = re.findall(r"(\d{1,2})\s*年(?:以上|及以上)?(?:[^。；;\n]{0,12})?(?:经验|经历)", text)
    return max((int(value) for value in matches), default=None)


def _extract_resume_years(text: str) -> int | None:
    explicit = re.findall(r"(\d{1,2})\s*年(?:以上|及以上)?(?:[^。；;\n]{0,12})?(?:经验|开发|工作)", text)
    return max((int(value) for value in explicit), default=None)


def _extract_education(text: str) -> str | None:
    found = [level for level in EDUCATION_RANK if level in text]
    return max(found, key=EDUCATION_RANK.get) if found else None


def _evidence_lines(text: str, aliases: tuple[str, ...], limit: int = 3) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    hits = [line for line in lines if _contains_alias(line, aliases)]
    return hits[:limit]


def analyze_match(resume_name: str, resume_text: str, job_description: str) -> MatchReport:
    if not job_description.strip():
        raise ValueError("职位描述不能为空。")
    if len(job_description) > 20_000:
        raise ValueError("职位描述不能超过 20,000 个字符。")

    required_skills = _extract_skills(job_description)
    resume_skills = set(_extract_skills(resume_text))
    matched_skills = [skill for skill in required_skills if skill in resume_skills]
    missing_skills = [skill for skill in required_skills if skill not in resume_skills]

    evidence = [
        RequirementEvidence(
            requirement=skill,
            matched=skill in resume_skills,
            evidence=_evidence_lines(resume_text, SKILL_ALIASES[skill]),
        )
        for skill in required_skills
    ]

    required_years = _extract_required_years(job_description)
    resume_years = _extract_resume_years(resume_text)
    required_education = _extract_education(job_description)
    resume_education = _extract_education(resume_text)

    skill_score = round(100 * len(matched_skills) / len(required_skills), 1) if required_skills else 0.0
    experience_score = (
        min(100.0, round(100 * resume_years / required_years, 1))
        if required_years and resume_years is not None
        else (0.0 if required_years else 100.0)
    )
    education_score = (
        100.0
        if required_education and resume_education
        and EDUCATION_RANK[resume_education] >= EDUCATION_RANK[required_education]
        else (0.0 if required_education else 100.0)
    )

    weighted_parts: list[tuple[float, float]] = []
    if required_skills:
        weighted_parts.append((skill_score, 70.0))
    if required_years:
        weighted_parts.append((experience_score, 15.0))
    if required_education:
        weighted_parts.append((education_score, 15.0))
    overall = (
        round(sum(score * weight for score, weight in weighted_parts) / sum(weight for _, weight in weighted_parts), 1)
        if weighted_parts
        else 0.0
    )

    recommendations = [f"如果确有经验，在项目成果中补充 {skill} 的具体使用证据。" for skill in missing_skills]
    if required_years and resume_years is None:
        recommendations.append("用明确起止时间或工作年限呈现相关经验，避免系统无法判断。")
    if required_education and resume_education is None:
        recommendations.append("在教育经历中明确填写学历；不得为了匹配岗位虚构学历。")
    if not recommendations:
        recommendations.append("关键词覆盖良好，下一步应强化量化成果和岗位职责对应关系。")

    limitations = ["当前分数是可解释的规则基线，不代表招聘方最终判断。"]
    if not required_skills:
        limitations.append("JD 中未识别到技能词，建议补充更完整的职位描述。")
    limitations.append("系统只把简历中可定位的文字当作证据，不会补写不存在的经历。")

    return MatchReport(
        resume_name=resume_name,
        overall_score=overall,
        required_skills=required_skills,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        required_experience_years=required_years,
        detected_experience_years=resume_years,
        required_education=required_education,
        detected_education=resume_education,
        evidence=evidence,
        score_breakdown=ScoreBreakdown(
            skills=skill_score,
            experience=experience_score,
            education=education_score,
        ),
        recommendations=recommendations,
        limitations=limitations,
    )
