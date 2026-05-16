# -*- coding: utf-8 -*-
from typing import Literal

from pydantic import BaseModel, Field

LevelLiteral = Literal["safe", "caution", "danger"]
GradeKoLiteral = Literal["안전", "주의", "위험"]


class RiskFactor(BaseModel):
    type: str
    description: str
    score: int | None = None


class ExplainRequest(BaseModel):
    """백엔드 규칙/ML 분석 결과를 받아 사용자용 문구를 생성할 때 사용."""

    url: str
    normalized_url: str | None = None
    final_url: str | None = None
    hop_count: int | None = None

    score: int = Field(ge=0, le=100, description="0~100 위험 점수")
    level: LevelLiteral
    ml_phishing_probability_percent: float | None = Field(
        default=None,
        description=" ONNX 피싱 모델 확률(%), 선택",
    )

    risk_factors: list[RiskFactor] = Field(default_factory=list)

    # 프론트/백 호환용 (한글 등급만 올 경우)
    grade_display: GradeKoLiteral | None = None


LlmProviderLiteral = Literal["solar", "gemini", "template"]


class ExplainResponse(BaseModel):
    explanation: str = Field(description="2~3문장 내 위험/안전 설명")
    action_guide: list[str] = Field(
        description="구체적인 행동 지침, 짧은 문장 리스트",
    )
    used_llm: bool = Field(description="실제 LLM(Solar/Gemini) 호출 성공 여부")
    model: str | None = Field(default=None, description="호출한 모델명")
    llm_provider: LlmProviderLiteral | None = Field(
        default=None,
        description="solar | gemini | template(키 없음·파싱 실패 시 규칙 문구)",
    )


class AnalyzeRequest(BaseModel):
    """URL만 받아 ML·리다이렉트·설명까지 한 번에 처리할 때 사용."""

    url: str


class AnalyzeResponse(BaseModel):
    url: str
    final_url: str
    hop_count: int
    ml_score: float | None
    total_score: int
    level: LevelLiteral
    grade_display: GradeKoLiteral
    risk_factors: list[RiskFactor]
    explanation: str
    action_guide: list[str]
    used_llm: bool
    model: str | None
