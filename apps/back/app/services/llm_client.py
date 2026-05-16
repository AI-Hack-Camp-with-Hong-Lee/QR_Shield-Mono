from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.models.risk import RiskLevel


@dataclass(frozen=True)
class LlmRiskFactor:
    type: str
    description: str
    score: int | None = None


@dataclass(frozen=True)
class LlmScoreResult:
    final_url: str
    hop_count: int
    ml_score: float | None
    ml_available: bool
    redirect_score: int
    risk_factors: list[LlmRiskFactor] = field(default_factory=list)
    domain_changed: bool = False
    is_short_url: bool = False
    suspicious_tld: bool = False


@dataclass(frozen=True)
class LlmExplainResult:
    explanation: str
    action_guide: list[str]
    used_llm: bool
    model: str | None = None


class LlmClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = httpx.Timeout(timeout_seconds)

    def score(self, url: str) -> LlmScoreResult:
        response = httpx.post(
            f"{self._base_url}/api/agent/score",
            json={"url": url},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return _parse_score_response(response.json())

    def explain(
        self,
        *,
        url: str,
        normalized_url: str,
        final_url: str,
        hop_count: int,
        score: int,
        level: RiskLevel,
        ml_score: float | None,
        risk_factors: list[LlmRiskFactor],
    ) -> LlmExplainResult:
        response = httpx.post(
            f"{self._base_url}/api/agent/explain",
            json={
                "url": url,
                "normalized_url": normalized_url,
                "final_url": final_url,
                "hop_count": hop_count,
                "score": score,
                "level": level.value,
                "ml_phishing_probability_percent": ml_score,
                "risk_factors": [
                    {
                        "type": factor.type,
                        "description": factor.description,
                        "score": factor.score,
                    }
                    for factor in risk_factors
                ],
                "grade_display": _grade_display(level),
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        guides = body.get("action_guide") or []
        if isinstance(guides, str):
            guides = [guides]
        return LlmExplainResult(
            explanation=str(body.get("explanation") or "").strip(),
            action_guide=[str(guide).strip() for guide in guides if str(guide).strip()],
            used_llm=bool(body.get("used_llm")),
            model=body.get("model"),
        )


def _parse_score_response(body: dict[str, Any]) -> LlmScoreResult:
    factors = [
        LlmRiskFactor(
            type=str(item.get("type") or "unknown"),
            description=str(item.get("description") or "").strip(),
            score=item.get("score"),
        )
        for item in body.get("risk_factors", [])
        if isinstance(item, dict)
    ]

    return LlmScoreResult(
        final_url=str(body.get("final_url") or body.get("url") or ""),
        hop_count=int(body.get("hop_count") or 0),
        ml_score=_optional_float(body.get("ml_score")),
        ml_available=bool(body.get("ml_available")),
        redirect_score=int(body.get("redirect_score") or 0),
        risk_factors=factors,
        domain_changed=bool(body.get("domain_changed")),
        is_short_url=bool(body.get("is_short_url")),
        suspicious_tld=bool(body.get("suspicious_tld")),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _grade_display(level: RiskLevel) -> str:
    if level is RiskLevel.DANGER:
        return "위험"
    if level is RiskLevel.CAUTION:
        return "주의"
    return "안전"
