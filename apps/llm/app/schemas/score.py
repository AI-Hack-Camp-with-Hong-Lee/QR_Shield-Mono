# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field

from app.schemas.explain import RiskFactor


class ScoreRequest(BaseModel):
    """백엔드가 URL만 넘겨 ML·리다이렉트 중간 결과를 받을 때 사용."""

    url: str = Field(..., min_length=1)


class ScoreResponse(BaseModel):
    """최종 점수·등급 없음 — 백에서 규칙과 합산."""

    url: str
    final_url: str
    hop_count: int
    ml_score: float | None = Field(
        default=None,
        description="ONNX 피싱 추정 0~100. 모델 실패 시 null",
    )
    ml_available: bool = Field(
        description="ONNX 추론 성공 여부. false면 ml_score는 null",
    )
    redirect_score: int = Field(
        ge=0,
        description="리다이렉트·단축 URL 등 규칙 가산 합",
    )
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    domain_changed: bool = False
    is_short_url: bool = False
    suspicious_tld: bool = False
