from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from uuid import uuid4

from app.core.config import settings
from app.models.risk import RiskLevel, RiskSignal
from app.schemas.analysis import ScanResultResponse
from app.services.llm_client import LlmClient, LlmExplainResult, LlmRiskFactor, LlmScoreResult
from app.services.url_parser import ParsedUrl, is_ip_address, parse_url


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
    def __init__(
        self,
        llm_client: LlmClient | None = None,
        ml_score_weight: float = 0.4,
    ) -> None:
        self._llm_client = llm_client
        self._ml_score_weight = ml_score_weight

    def analyze(self, url: str) -> ScanResultResponse:
        parsed_url = parse_url(url)
        rule_signals = self._collect_signals(parsed_url)
        llm_score = self._score_with_llm(parsed_url)

        score = self._combined_score(rule_signals, llm_score)
        risk_level = self._risk_level(score)
        signal_labels = self._signal_labels(rule_signals, llm_score)

        llm_explain = self._explain_with_llm(
            parsed_url=parsed_url,
            score=score,
            risk_level=risk_level,
            llm_score=llm_score,
        )

        return ScanResultResponse(
            id=str(uuid4()),
            url=parsed_url.normalized,
            riskLevel=risk_level.value,
            score=score,
            explanation=(
                llm_explain.explanation
                if llm_explain and llm_explain.explanation
                else self._explanation(risk_level, signal_labels)
            ),
            actionGuide=(
                "\n".join(llm_explain.action_guide)
                if llm_explain and llm_explain.action_guide
                else self._action_guide(risk_level)
            ),
            signals=signal_labels,
            scannedAt=datetime.now(UTC),
        )

    def _score_with_llm(self, parsed_url: ParsedUrl) -> LlmScoreResult | None:
        if self._llm_client is None or not parsed_url.is_valid_web_url:
            return None
        try:
            return self._llm_client.score(parsed_url.normalized)
        except Exception:
            return None

    def _explain_with_llm(
        self,
        *,
        parsed_url: ParsedUrl,
        score: int,
        risk_level: RiskLevel,
        llm_score: LlmScoreResult | None,
    ) -> LlmExplainResult | None:
        if self._llm_client is None or not parsed_url.is_valid_web_url:
            return None
        risk_factors = llm_score.risk_factors if llm_score else []
        try:
            return self._llm_client.explain(
                url=parsed_url.original,
                normalized_url=parsed_url.normalized,
                final_url=llm_score.final_url if llm_score else parsed_url.normalized,
                hop_count=llm_score.hop_count if llm_score else 0,
                score=score,
                level=risk_level,
                ml_score=llm_score.ml_score if llm_score else None,
                risk_factors=risk_factors,
            )
        except Exception:
            return None

    def _combined_score(
        self,
        rule_signals: list[RiskSignal],
        llm_score: LlmScoreResult | None,
    ) -> int:
        score = sum(signal.score for signal in rule_signals)
        if llm_score is not None:
            score += llm_score.redirect_score
            if llm_score.ml_available and llm_score.ml_score is not None:
                score += round(llm_score.ml_score * self._ml_score_weight)
        return min(score, 100)

    @staticmethod
    def _signal_labels(
        rule_signals: list[RiskSignal],
        llm_score: LlmScoreResult | None,
    ) -> list[str]:
        labels = [signal.label for signal in rule_signals]
        if llm_score is None:
            return labels

        for factor in llm_score.risk_factors:
            if factor.description and factor.description not in labels:
                labels.append(factor.description)

        if llm_score.ml_available and llm_score.ml_score is not None and llm_score.ml_score >= 70:
            label = f"ML 피싱 의심 점수 높음({llm_score.ml_score:.0f}%)"
            if label not in labels:
                labels.append(label)

        return labels

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
    def _risk_level(score: int) -> RiskLevel:
        if score >= 70:
            return RiskLevel.DANGER
        if score >= 35:
            return RiskLevel.CAUTION
        return RiskLevel.SAFE

    @staticmethod
    def _explanation(risk_level: RiskLevel, signals: list[str]) -> str:
        if risk_level is RiskLevel.DANGER:
            return (
                "이 URL은 룰 기반 검사에서 높은 위험 신호가 다수 감지되었습니다. "
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
        return "이 URL은 현재 룰 기반 검사에서 뚜렷한 위험 신호가 감지되지 않았습니다."

    @staticmethod
    def _action_guide(risk_level: RiskLevel) -> str:
        if risk_level is RiskLevel.DANGER:
            return "접속하지 마세요. 이미 열었다면 개인정보 입력을 중단하고 브라우저 탭을 닫으세요."
        if risk_level is RiskLevel.CAUTION:
            return "접속 전 발신자와 도메인을 확인하고, 로그인/결제/개인정보 입력은 피하세요."
        return "공식 출처에서 받은 QR 코드라면 접속해도 됩니다. 그래도 개인정보 입력 전 주소를 한 번 더 확인하세요."


@lru_cache
def get_risk_analysis_service() -> RiskAnalysisService:
    llm_client = None
    if settings.llm_enabled:
        llm_client = LlmClient(
            base_url=settings.llm_base_url,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return RiskAnalysisService(
        llm_client=llm_client,
        ml_score_weight=settings.llm_ml_score_weight,
    )
