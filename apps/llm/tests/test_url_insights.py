# -*- coding: utf-8 -*-
from app.schemas.explain import ExplainRequest, RiskFactor
from app.services.url_insights import build_url_insights


def test_insights_for_go_kr_safe_url():
    req = ExplainRequest(
        url="https://science.go.kr",
        normalized_url="https://science.go.kr",
        score=10,
        level="safe",
        ml_phishing_probability_percent=0.0,
    )
    lines = build_url_insights(req)
    text = "\n".join(lines)
    assert "science.go.kr" in text
    assert "https" in text.lower()


def test_insights_short_url_and_final_host_change():
    req = ExplainRequest(
        url="https://bit.ly/test",
        normalized_url="https://bit.ly/test",
        final_url="https://evil-example.xyz/login",
        hop_count=2,
        score=65,
        level="caution",
        ml_phishing_probability_percent=50.0,
        risk_factors=[
            RiskFactor(type="short_url", description="단축 URL", score=20),
        ],
    )
    lines = build_url_insights(req)
    text = "\n".join(lines)
    assert "bit.ly" in text or "단축" in text
    assert "evil-example.xyz" in text
    assert "리다이렉트" in text or "최종" in text


def test_insights_path_login_keyword():
    req = ExplainRequest(
        url="https://bank-secure-verify.example.com/account/login",
        score=80,
        level="danger",
    )
    lines = build_url_insights(req)
    text = "\n".join(lines)
    assert "login" in text or "account" in text


def test_build_user_prompt_includes_insights_block():
    from app.prompts.explain import build_user_prompt
    from app.services.url_insights import build_url_snapshot

    req = ExplainRequest(
        url="https://bit.ly/x",
        score=50,
        level="caution",
        risk_factors=[],
    )
    prompt = build_user_prompt(
        req,
        url_snapshot=build_url_snapshot(req),
        url_insights=["단축 URL 서비스 도메인"],
    )
    assert "[URL 구조·패턴 분석]" in prompt
    assert "bit.ly" in prompt
    assert "복사 금지" in prompt
    assert "단축 URL을 사용하고 있어" not in prompt
