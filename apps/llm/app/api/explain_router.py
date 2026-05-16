# -*- coding: utf-8 -*-
import asyncio
from urllib.parse import urlparse

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.ml.model import predict_phishing_score
from app.ml.redirect import calculate_redirect_score, trace_redirects
from app.schemas.explain import (
    AnalyzeRequest,
    AnalyzeResponse,
    ExplainRequest,
    ExplainResponse,
    GradeKoLiteral,
    LevelLiteral,
    RiskFactor,
)
from app.services.gemini_service import explain_with_gemini

router = APIRouter(tags=["explain"])


def get_settings() -> Settings:
    return Settings()


def _normalize_url(u: str) -> str:
    s = u.strip()
    if not urlparse(s).scheme:
        return "https://" + s
    return s


def _level_and_grade(total_score: int) -> tuple[LevelLiteral, GradeKoLiteral]:
    if total_score >= 70:
        return "danger", "위험"
    if total_score >= 40:
        return "caution", "주의"
    return "safe", "안전"


@router.post("/api/agent/explain", response_model=ExplainResponse)
async def agent_explain(
    body: ExplainRequest,
    settings: Settings = Depends(get_settings),
) -> ExplainResponse:
    return await asyncio.to_thread(explain_with_gemini, settings, body)


@router.post("/api/agent/analyze", response_model=AnalyzeResponse)
async def agent_analyze(
    body: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    url = body.url.strip()
    norm = _normalize_url(url)

    ml_task = asyncio.to_thread(predict_phishing_score, url)
    trace_task = trace_redirects(url, max_hops=5)
    ml_score_raw, redirect_info = await asyncio.gather(ml_task, trace_task)

    redirect_score, factor_dicts = calculate_redirect_score(redirect_info)
    risk_factors = [RiskFactor(**d) for d in factor_dicts]

    if ml_score_raw < 0:
        ml_int = 50
        ml_score_out: float | None = None
    else:
        ml_int = int(ml_score_raw)
        ml_score_out = float(ml_score_raw)

    total_score = min(ml_int + redirect_score, 100)
    level, grade_ko = _level_and_grade(total_score)

    explain_body = ExplainRequest(
        url=url,
        normalized_url=norm,
        final_url=str(redirect_info.get("final_url") or norm),
        hop_count=int(redirect_info.get("hop_count") or 0),
        score=total_score,
        level=level,
        ml_phishing_probability_percent=ml_score_out,
        risk_factors=risk_factors,
        grade_display=grade_ko,
    )

    gemini = await asyncio.to_thread(explain_with_gemini, settings, explain_body)

    return AnalyzeResponse(
        url=url,
        final_url=str(redirect_info.get("final_url") or norm),
        hop_count=int(redirect_info.get("hop_count") or 0),
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
