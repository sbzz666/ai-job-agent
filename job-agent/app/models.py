"""Shared data contracts for the job analysis workflow."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RequirementEvidence(BaseModel):
    requirement: str
    matched: bool
    evidence: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    skills: float = Field(ge=0, le=100)
    experience: float = Field(ge=0, le=100)
    education: float = Field(ge=0, le=100)


class MatchReport(BaseModel):
    task_id: str | None = None
    resume_name: str
    overall_score: float = Field(ge=0, le=100)
    required_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    required_experience_years: int | None = None
    detected_experience_years: int | None = None
    required_education: str | None = None
    detected_education: str | None = None
    evidence: list[RequirementEvidence]
    score_breakdown: ScoreBreakdown
    recommendations: list[str]
    limitations: list[str]
    created_at: datetime = Field(default_factory=datetime.now)


class TaskSummary(BaseModel):
    task_id: str
    resume_name: str
    overall_score: float
    created_at: datetime


class InterviewQuestion(BaseModel):
    question: str
    evaluation_focus: str
    reference_answer: str


class AICareerGuidance(BaseModel):
    resume_suggestions: list[str] = Field(min_length=1)
    self_introduction: str = Field(min_length=20)
    interview_questions: list[InterviewQuestion] = Field(min_length=1)
    fact_check_warnings: list[str] = Field(default_factory=list)
    verified: bool = True
    model: str


class AIQuestionAnswer(BaseModel):
    answer: str
    evidence: list[str] = Field(default_factory=list)
    refused: bool = False
    model: str
