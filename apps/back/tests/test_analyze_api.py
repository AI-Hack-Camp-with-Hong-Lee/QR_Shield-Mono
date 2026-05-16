from pydantic import ValidationError

from app.api.routes.analyze import analyze_url
from app.api.routes.health import health_check
from app.main import app
from app.schemas.analysis import AnalyzeUrlRequest
from app.services.risk_engine import RiskAnalysisService


def test_routes_are_registered():
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/api/v1/analyze" in paths


def test_health_check():
    assert health_check() == {"status": "ok"}


def test_analyze_response_matches_front_contract():
    payload = AnalyzeUrlRequest(url="https://example.com")
    result = analyze_url(payload, RiskAnalysisService())
    body = result.model_dump(by_alias=True)

    assert set(body) == {
        "id",
        "url",
        "riskLevel",
        "score",
        "explanation",
        "actionGuide",
        "signals",
        "scannedAt",
    }
    assert body["url"] == "https://example.com"
    assert body["riskLevel"] == "safe"
    assert body["score"] == 0
    assert isinstance(body["signals"], list)


def test_analyze_rejects_empty_url():
    try:
        AnalyzeUrlRequest(url="   ")
    except ValidationError:
        return

    raise AssertionError("empty url should be rejected")
