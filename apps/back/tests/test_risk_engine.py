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
