from app.models.risk import RiskLevel
from app.services.llm_client import LlmExplainResult, LlmRiskFactor, LlmScoreResult
from app.services.risk_engine import RiskAnalysisService


async def test_safe_url_has_safe_risk_level():
    result = await RiskAnalysisService().analyze("https://example.com")

    assert result.risk_level == "safe"
    assert result.score == 0
    assert result.signals == []


async def test_url_without_scheme_is_normalized_to_https():
    result = await RiskAnalysisService().analyze("example.com/path?utm=qr")

    assert result.url == "https://example.com/path?utm=qr"
    assert result.risk_level == "safe"


async def test_shortener_login_url_is_caution():
    result = await RiskAnalysisService().analyze("https://bit.ly/login-verify")

    assert result.risk_level == "caution"
    assert "단축 URL 사용" in result.signals
    assert "계정/결제 관련 의심 키워드 포함" in result.signals


async def test_high_risk_ip_url_is_danger():
    result = await RiskAnalysisService().analyze("http://192.168.0.1/phishing?token=abc")

    assert result.risk_level == "danger"
    assert "HTTPS가 아닌 HTTP 사용" in result.signals
    assert "IP 주소 직접 접근" in result.signals
    assert "고위험 키워드 포함" in result.signals
    assert "민감한 파라미터 포함" in result.signals


async def test_non_web_qr_payload_is_danger():
    result = await RiskAnalysisService().analyze("WIFI:T:WPA;S:test;P:password;;")

    assert result.risk_level == "danger"
    assert result.score == 85
    assert result.signals == ["HTTP/HTTPS URL이 아님"]


def test_llm_score_and_explain_are_used_when_client_is_configured():
    result = RiskAnalysisService(
        llm_client=FakeLlmClient(),
        ml_score_weight=0.5,
    ).analyze("https://example.com")

    assert result.risk_level == "caution"
    assert result.score == 50
    assert result.explanation == "LLM explanation for caution 50"
    assert result.action_guide == "공식 앱에서 확인하세요.\n개인정보 입력을 피하세요."
    assert "주소가 1회 다른 곳으로 연결(리다이렉트)되었습니다." in result.signals
    assert "ML 피싱 의심 점수 높음(80%)" in result.signals


def test_llm_failure_falls_back_to_rule_based_result():
    result = RiskAnalysisService(llm_client=FailingLlmClient()).analyze(
        "https://example.com"
    )

    assert result.risk_level == "safe"
    assert result.score == 0
    assert result.signals == []
