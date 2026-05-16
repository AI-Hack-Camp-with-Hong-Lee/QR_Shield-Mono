from __future__ import annotations

from app.models.risk import RiskLevel


CAUTION_THRESHOLD = 40
DANGER_THRESHOLD = 70

_LEVEL_KO = {
    RiskLevel.SAFE: "안전",
    RiskLevel.CAUTION: "주의",
    RiskLevel.DANGER: "위험",
}


def combine_final_score(
    rule_score: int,
    ml_score: float | None,
    ml_available: bool,
    redirect_score: int,
) -> int:
    """규칙 점수 + (ML + 리다이렉트) 중간 점수를 합산해 0~100으로 제한."""
    ml_part = int(ml_score) if ml_available and ml_score is not None else 0
    agent_part = min(ml_part + max(redirect_score, 0), 100)
    return min(rule_score + agent_part, 100)


def risk_level_from_score(score: int) -> RiskLevel:
    if score >= DANGER_THRESHOLD:
        return RiskLevel.DANGER
    if score >= CAUTION_THRESHOLD:
        return RiskLevel.CAUTION
    return RiskLevel.SAFE


def level_to_api(level: RiskLevel) -> str:
    return level.value


def grade_display_ko(level: RiskLevel) -> str:
    return _LEVEL_KO[level]
