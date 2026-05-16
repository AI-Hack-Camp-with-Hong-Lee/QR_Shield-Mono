# -*- coding: utf-8 -*-
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.explain import RiskFactor
from app.services.middle_score import (
    _append_ml_high_risk_if_needed,
    normalize_url,
)


def test_normalize_url_adds_https():
    assert normalize_url("example.com") == "https://example.com"
    assert normalize_url("https://a.com") == "https://a.com"


def test_append_ml_high_risk_when_only_ml_is_high():
    factors = _append_ml_high_risk_if_needed([], True, 85.0)
    assert len(factors) == 1
    assert factors[0].type == "ml_high_risk"


def test_append_ml_high_risk_skips_when_redirect_signal_exists():
    existing = [
        RiskFactor(type="short_url", description="단축 URL", score=20),
    ]
    factors = _append_ml_high_risk_if_needed(existing, True, 90.0)
    assert len(factors) == 1
    assert factors[0].type == "short_url"


@pytest.mark.asyncio
async def test_compute_middle_score_uses_parallel_tasks():
    from app.services import middle_score as ms

    with (
        patch.object(
            ms,
            "predict_phishing_score",
            return_value=12.0,
        ),
        patch.object(
            ms,
            "trace_redirects",
            new=AsyncMock(
                return_value={
                    "final_url": "https://example.com",
                    "hop_count": 0,
                    "domain_changed": False,
                    "is_short_url": False,
                    "suspicious_tld": False,
                }
            ),
        ),
        patch.object(
            ms,
            "calculate_redirect_score",
            return_value=(0, []),
        ),
    ):
        data = await ms.compute_middle_score("https://example.com")

    assert data["ml_available"] is True
    assert data["ml_score"] == 12.0
    assert data["redirect_score"] == 0
