from __future__ import annotations

import logging
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from uuid import uuid4

from app.clients.llm_client import LlmClient, LlmServiceError, get_llm_client
from app.models.risk import RiskLevel, RiskSignal
from app.schemas.analysis import ScanResultResponse
from app.services.score_aggregator import (
    combine_final_score,
    grade_display_ko,
    level_to_api,
    risk_level_from_score,
)
from app.services.url_parser import ParsedUrl, is_ip_address, parse_url

logger = logging.getLogger(__name__)

SHORTENER_DOMAINS = {
    "bit.ly",
    "buff.ly",
    "cutt.ly",
    "goo.gl",
    "is.gd",
    "ow.ly",
    "rebrand.ly",
    "rb.gy",
    "s.id",
    "t.co",
    "tinyurl.com",
}

HIGH_RISK_KEYWORDS = {
    "phishing",
    "malware",
    "evil",
    "steal",
    "hack",
    "credential",
    "password",
}

CAUTION_KEYWORDS = {
    "account",
    "bank",
    "bonus",
    "claim",
    "crypto",
    "free",
    "gift",
    "login",
    "pay",
    "recover",
    "secure",
    "support",
    "update",
    "verify",
    "wallet",
}

SUSPICIOUS_TLDS = {"zip", "mov", "click", "top", "xyz", "icu", "work", "rest"}
SENSITIVE_PARAMS = {"token", "password", "pass", "otp", "code", "session", "redirect", "url", "next"}


class RiskAnalysisService:
    def __init__(self, llm_client: LlmClient | None = None) -> None:
        self._llm = llm_client or get_llm_client()

    async def analyze(self, url: str) -> ScanResultResponse:
        parsed_url = parse_url(url)
        signals = self._collect_signals(parsed_url)
        rule_score = min(sum(signal.score for signal in signals), 100)
        signal_labels = [signal.label for signal in signals]

        middle: dict[str, Any] | None = None
        if parsed_url.is_valid_web_url and self._llm.enabled:
            try:
                middle = await self._llm.fetch_score(parsed_url.normalized)
            except Exception as exc:
                logger.warning("LLM score call failed: %s", exc)

        if middle:
            final_score = combine_final_score(
                rule_score,
                middle.get("ml_score"),
                bool(middle.get("ml_available")),
                int(middle.get("redirect_score") or 0),
            )
            risk_level = risk_level_from_score(final_score)
            llm_factors = middle.get("risk_factors") or []
            merged_signals = _merge_signal_labels(signal_labels, llm_factors)
            explanation, action_guide = await self._explain_with_llm(
                parsed_url=parsed_url,
                middle=middle,
                final_score=final_score,
                risk_level=risk_level,
                rule_labels=signal_labels,
                rule_factors=_rule_risk_factors(signals),
                llm_factors=llm_factors,
            )
            return ScanResultResponse(
                id=str(uuid4()),
                url=parsed_url.normalized,
                riskLevel=level_to_api(risk_level),
                score=final_score,
                explanation=explanation,
                actionGuide=action_guide,
                signals=merged_signals,
                scannedAt=datetime.now(UTC),
            )

        risk_level = risk_level_from_score(rule_score)
        return ScanResultResponse(
            id=str(uuid4()),
            url=parsed_url.normalized,
            riskLevel=level_to_api(risk_level),
            score=rule_score,
            explanation=self._explanation(risk_level, signal_labels),
            actionGuide=self._action_guide(risk_level),
            signals=signal_labels,
            scannedAt=datetime.now(UTC),
        )

    async def _explain_with_llm(
        self,
        *,
        parsed_url: ParsedUrl,
        middle: dict[str, Any],
        final_score: int,
        risk_level: RiskLevel,
        rule_labels: list[str],
        rule_factors: list[dict[str, Any]],
        llm_factors: list[dict[str, Any]],
    ) -> tuple[str, str]:
        combined_factors = [*llm_factors, *rule_factors]
        payload = {
            "url": middle.get("url") or parsed_url.normalized,
            "normalized_url": parsed_url.normalized,
            "final_url": middle.get("final_url"),
            "hop_count": middle.get("hop_count"),
            "score": final_score,
            "level": level_to_api(risk_level),
            "ml_phishing_probability_percent": middle.get("ml_score"),
            "risk_factors": combined_factors,
            "grade_display": grade_display_ko(risk_level),
        }
        try:
            result = await self._llm.fetch_explain(payload)
            explanation = str(result.get("explanation", "")).strip()
            guides = result.get("action_guide") or []
            if isinstance(guides, str):
                guides = [guides]
            action_guide = "\n".join(
                str(item).strip() for item in guides if str(item).strip()
            )
            if explanation and action_guide:
                return explanation, action_guide
        except (LlmServiceError, Exception) as exc:
            logger.warning("LLM explain call failed: %s", exc)

        factor_labels = [
            str(f.get("description", "")).strip()
            for f in combined_factors
            if f.get("description")
        ]
        return (
            self._explanation(risk_level, factor_labels or rule_labels),
            self._action_guide(risk_level),
        )

    def _collect_signals(self, parsed_url: ParsedUrl) -> list[RiskSignal]:
        signals: list[RiskSignal] = []
        hostname = parsed_url.hostname
        full_url = parsed_url.normalized.lower()
        path_and_query = parsed_url.path_and_query.lower()

        if not parsed_url.is_valid_web_url:
            return [RiskSignal(parsed_url.validation_signal or "유효하지 않은 URL", 85)]

        if parsed_url.scheme == "http":
            signals.append(RiskSignal("HTTPS가 아닌 HTTP 사용", 15))

        if hostname in SHORTENER_DOMAINS:
            signals.append(RiskSignal("단축 URL 사용", 25))

        if is_ip_address(hostname):
            signals.append(RiskSignal("IP 주소 직접 접근", 25))

        if hostname.startswith("xn--") or ".xn--" in hostname:
            signals.append(RiskSignal("국제화 도메인(Punycode) 사용", 20))

        if "@" in parsed_url.parsed.netloc:
            signals.append(RiskSignal("사용자 정보가 포함된 URL", 35))

        tld = hostname.rsplit(".", 1)[-1] if "." in hostname else ""
        if tld in SUSPICIOUS_TLDS:
            signals.append(RiskSignal("주의가 필요한 최상위 도메인", 10))

        high_risk_matches = sorted(keyword for keyword in HIGH_RISK_KEYWORDS if keyword in full_url)
        if high_risk_matches:
            signals.append(RiskSignal("고위험 키워드 포함", 35))

        caution_matches = sorted(keyword for keyword in CAUTION_KEYWORDS if keyword in full_url)
        if caution_matches:
            signals.append(RiskSignal("계정/결제 관련 의심 키워드 포함", 15))

        if len(parsed_url.normalized) > 160:
            signals.append(RiskSignal("비정상적으로 긴 URL", 15))
        elif len(parsed_url.normalized) > 100:
            signals.append(RiskSignal("긴 URL", 8))

        if parsed_url.parsed.query:
            param_names = {
                key.split("=", 1)[0].lower()
                for key in parsed_url.parsed.query.split("&")
                if key
            }
            if param_names & SENSITIVE_PARAMS:
                signals.append(RiskSignal("민감한 파라미터 포함", 15))
            elif len(param_names) >= 5:
                signals.append(RiskSignal("파라미터가 많은 URL", 8))

        if path_and_query.count("//") > 0:
            signals.append(RiskSignal("경로에 중첩 URL 패턴 포함", 12))

        if hostname.count("-") >= 3:
            signals.append(RiskSignal("하이픈이 많은 도메인", 8))

        return signals

    @staticmethod
    def _explanation(risk_level: RiskLevel, signals: list[str]) -> str:
        if risk_level is RiskLevel.DANGER:
            return (
                "이 URL은 자동 검사에서 높은 위험 신호가 다수 감지되었습니다. "
                f"주요 신호는 {', '.join(signals)}입니다."
            )
        if risk_level is RiskLevel.CAUTION:
            return (
                "이 URL은 즉시 악성으로 단정할 수는 없지만 주의가 필요한 신호가 감지되었습니다. "
                f"확인된 신호는 {', '.join(signals)}입니다."
            )
        if signals:
            return (
                "이 URL은 낮은 수준의 주의 신호가 있으나 전체 위험도는 낮게 평가되었습니다. "
                f"확인된 신호는 {', '.join(signals)}입니다."
            )
        return "이 URL은 현재 자동 검사에서 뚜렷한 위험 신호가 감지되지 않았습니다."

    @staticmethod
    def _action_guide(risk_level: RiskLevel) -> str:
        if risk_level is RiskLevel.DANGER:
            return "접속하지 마세요. 이미 열었다면 개인정보 입력을 중단하고 브라우저 탭을 닫으세요."
        if risk_level is RiskLevel.CAUTION:
            return "접속 전 발신자와 도메인을 확인하고, 로그인/결제/개인정보 입력은 피하세요."
        return "공식 출처에서 받은 QR 코드라면 접속해도 됩니다. 그래도 개인정보 입력 전 주소를 한 번 더 확인하세요."


def _rule_risk_factors(signals: list[RiskSignal]) -> list[dict[str, Any]]:
    return [
        {
            "type": "rule",
            "description": signal.label,
            "score": signal.score,
        }
        for signal in signals
    ]


def _merge_signal_labels(
    rule_labels: list[str],
    llm_factors: list[dict[str, Any]],
) -> list[str]:
    merged = list(rule_labels)
    seen = set(rule_labels)
    for factor in llm_factors:
        description = str(factor.get("description", "")).strip()
        if description and description not in seen:
            merged.append(description)
            seen.add(description)
    return merged


@lru_cache
def get_risk_analysis_service() -> RiskAnalysisService:
    return RiskAnalysisService()
