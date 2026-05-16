# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from app.ml.model import predict_phishing_score
from app.ml.redirect import calculate_redirect_score, trace_redirects
from app.schemas.explain import RiskFactor

ML_HIGH_RISK_THRESHOLD = 70.0


def normalize_url(u: str) -> str:
    s = u.strip()
    if not urlparse(s).scheme:
        return "https://" + s
    return s


def _append_ml_high_risk_if_needed(
    risk_factors: list[RiskFactor],
    ml_available: bool,
    ml_score: float | None,
) -> list[RiskFactor]:
    if not ml_available or ml_score is None:
        return risk_factors
    if ml_score < ML_HIGH_RISK_THRESHOLD:
        return risk_factors
    if any(f.type == "ml_high_risk" for f in risk_factors):
        return risk_factors
    # 리다이렉트 신호가 없을 때 ML만 높은 경우 근거 제공
    redirect_types = {
        "short_url",
        "redirect",
        "excessive_redirect",
        "domain_changed",
        "suspicious_tld",
    }
    has_redirect_signal = any(f.type in redirect_types for f in risk_factors)
    if has_redirect_signal:
        return risk_factors
    return [
        *risk_factors,
        RiskFactor(
            type="ml_high_risk",
            description=(
                "URL 패턴 분석 모델에서 피싱과 유사한 특징이 "
                f"높게 감지되었습니다(약 {ml_score:.0f}%)."
            ),
            score=int(min(ml_score, 100)),
        ),
    ]


async def compute_middle_score(url: str) -> dict:
    """ML + HEAD 리다이렉트 중간 패키지. 최종 등급·총점은 포함하지 않음."""
    raw_url = url.strip()
    norm = normalize_url(raw_url)

    ml_score_raw, redirect_info = await asyncio.gather(
        asyncio.to_thread(predict_phishing_score, raw_url),
        trace_redirects(raw_url, max_hops=5),
    )

    if ml_score_raw < 0:
        ml_available = False
        ml_score_out: float | None = None
    else:
        ml_available = True
        ml_score_out = float(ml_score_raw)

    redirect_score, factor_dicts = calculate_redirect_score(redirect_info)
    risk_factors = [RiskFactor(**d) for d in factor_dicts]
    risk_factors = _append_ml_high_risk_if_needed(
        risk_factors, ml_available, ml_score_out
    )

    final_url = str(redirect_info.get("final_url") or norm)

    return {
        "url": raw_url,
        "final_url": final_url,
        "hop_count": int(redirect_info.get("hop_count") or 0),
        "ml_score": ml_score_out,
        "ml_available": ml_available,
        "redirect_score": redirect_score,
        "risk_factors": risk_factors,
        "domain_changed": bool(redirect_info.get("domain_changed")),
        "is_short_url": bool(redirect_info.get("is_short_url")),
        "suspicious_tld": bool(redirect_info.get("suspicious_tld")),
    }
