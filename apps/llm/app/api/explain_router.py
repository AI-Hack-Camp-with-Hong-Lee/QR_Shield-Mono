# -*- coding: utf-8 -*-
import asyncio

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.schemas.explain import (
    AnalyzeRequest,
    AnalyzeResponse,
    ExplainRequest,
    ExplainResponse,
    GradeKoLiteral,
    LevelLiteral,
)
from app.schemas.score import ScoreRequest, ScoreResponse
from app.services.gemini_service import explain_with_gemini
from app.services.middle_score import compute_middle_score, normalize_url

router = APIRouter(tags=["explain"])


def get_settings() -> Settings:
    return Settings()


def _level_and_grade(total_score: int) -> tuple[LevelLiteral, GradeKoLiteral]:
    if total_score >= 70:
        return "danger", "위험"
    if total_score >= 40:
        return "caution", "주의"
    return "safe", "안전"


def _provisional_total(ml_score: float | None, redirect_score: int) -> int:
    ml_part = int(ml_score) if ml_score is not None else 0
    return min(ml_part + redirect_score, 100)


@router.post(
    "/api/agent/score",
    response_model=ScoreResponse,
    summary="백 연동용 중간 점수 (ML + 리다이렉트)",
)
async def agent_score(body: ScoreRequest) -> ScoreResponse:
    data = await compute_middle_score(body.url)
    return ScoreResponse(**data)


@router.post("/api/agent/explain", response_model=ExplainResponse)
async def agent_explain(
    body: ExplainRequest,
    settings: Settings = Depends(get_settings),
) -> ExplainResponse:
    return await asyncio.to_thread(explain_with_gemini, settings, body)


@router.post(
    "/api/agent/analyze",
    response_model=AnalyzeResponse,
    deprecated=True,
    summary="[로컬 테스트용] score + explain 한 번에 (백은 /score + /explain 사용)",
)
async def agent_analyze(
    body: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    url = body.url.strip()
    norm = normalize_url(url)
    data = await compute_middle_score(url)

    ml_score_out = data["ml_score"]
    redirect_score = data["redirect_score"]
    risk_factors = data["risk_factors"]
    total_score = _provisional_total(ml_score_out, redirect_score)
    level, grade_ko = _level_and_grade(total_score)

    explain_body = ExplainRequest(
        url=url,
        normalized_url=norm,
        final_url=data["final_url"],
        hop_count=data["hop_count"],
        score=total_score,
        level=level,
        ml_phishing_probability_percent=ml_score_out,
        risk_factors=risk_factors,
        grade_display=grade_ko,
    )

    gemini = await asyncio.to_thread(explain_with_gemini, settings, explain_body)

    return AnalyzeResponse(
        url=url,
        final_url=data["final_url"],
        hop_count=data["hop_count"],
        ml_score=ml_score_out,
        total_score=total_score,
        level=level,
        grade_display=grade_ko,
        risk_factors=risk_factors,
        explanation=gemini.explanation,
        action_guide=gemini.action_guide,
        used_llm=gemini.used_llm,
        model=gemini.model,
    )
