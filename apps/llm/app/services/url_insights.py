# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

from app.schemas.explain import ExplainRequest

_CAUTION_PATH_KEYWORDS: frozenset[str] = frozenset(
    {
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
        "signin",
        "support",
        "update",
        "verify",
        "wallet",
    }
)

_HIGH_RISK_PATH_KEYWORDS: frozenset[str] = frozenset(
    {
        "credential",
        "evil",
        "hack",
        "malware",
        "password",
        "phishing",
        "steal",
    }
)

_SUSPICIOUS_TLDS: tuple[str, ...] = (
    ".xyz",
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",
    ".top",
    ".icu",
    ".info",
    ".zip",
    ".mov",
    ".click",
    ".work",
    ".rest",
)

_SHORT_HOSTS: frozenset[str] = frozenset(
    {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "short.io", "buff.ly"}
)

_IPV4_RE = re.compile(
    r"^(?:\d{1,3}\.){3}\d{1,3}$"
)


def _ensure_scheme(url: str) -> str:
    u = url.strip()
    if not u:
        return u
    if not urlparse(u).scheme:
        return "https://" + u
    return u


def _strip_www(host: str | None) -> str:
    if not host:
        return ""
    h = host.lower()
    return h[4:] if h.startswith("www.") else h


def _host_of(url: str) -> str:
    return _strip_www(urlparse(_ensure_scheme(url)).hostname)


def _subdomain_depth(host: str) -> int:
    if not host:
        return 0
    parts = host.split(".")
    return max(len(parts) - 2, 0)


def _has_suspicious_tld(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    return any(h.endswith(tld) for tld in _SUSPICIOUS_TLDS)


def _find_keywords(text: str, keywords: frozenset[str]) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for kw in sorted(keywords):
        if kw in lower:
            found.append(kw)
    return found


def _path_query_text(url: str) -> str:
    p = urlparse(_ensure_scheme(url))
    path = p.path or ""
    query = p.query or ""
    return f"{path}?{query}" if query else path


def _is_ip_host(host: str | None) -> bool:
    if not host:
        return False
    return bool(_IPV4_RE.match(host))


def build_url_snapshot(req: ExplainRequest) -> str:
    """LLM이 URL 문자열을 직접 읽도록 돕는 구조 요약 (한 블록)."""
    raw = (req.url or "").strip()
    norm = (req.normalized_url or raw).strip()
    parsed = urlparse(_ensure_scheme(norm or raw))
    host = parsed.hostname or "(호스트 없음)"
    path = parsed.path or "/"
    lines = [
        f"입력 URL: {raw or norm}",
        f"호스트(도메인): {host}",
        f"경로: {path}",
    ]
    if parsed.query:
        q = parsed.query
        lines.append(f"쿼리: {q[:160]}{'…' if len(q) > 160 else ''}")
    final = (req.final_url or "").strip()
    if final and final not in (raw, norm):
        fp = urlparse(_ensure_scheme(final))
        lines.append(
            f"최종 URL: {final} (호스트: {fp.hostname or '?'})"
        )
    return "\n".join(f"- {line}" for line in lines)


def build_url_insights(req: ExplainRequest) -> list[str]:
    """URL 문자열만으로 LLM에 넘길 구조·패턴 힌트 (외부 조회 없음)."""
    lines: list[str] = []

    raw = (req.url or "").strip()
    norm = (req.normalized_url or raw).strip()
    final = (req.final_url or "").strip()

    host = _host_of(norm or raw)
    final_host = _host_of(final) if final else ""

    if host:
        depth = _subdomain_depth(host)
        lines.append(f"접속 호스트: {host}")
        if depth >= 2:
            lines.append(
                f"서브도메인이 {depth}단계로 길어 실제 서비스명을 가리기 쉬운 형태입니다."
            )
        elif depth == 1:
            lines.append("서브도메인이 한 단계 있습니다.")

    scheme = urlparse(_ensure_scheme(norm or raw)).scheme.lower()
    if scheme == "http":
        lines.append("암호화되지 않은 http 연결입니다(주소창 자물쇠 없음).")
    elif scheme == "https":
        lines.append("https(암호화) 연결 형식입니다.")

    if _is_ip_host(host):
        lines.append("도메인 대신 IP 숫자 주소로 접속합니다(일반 서비스와 다름).")

    if host and _has_suspicious_tld(host):
        lines.append("흔하지 않은 최상위 도메인(TLD)을 사용합니다.")

    if host and _strip_www(host) in _SHORT_HOSTS:
        lines.append("단축 URL 서비스 도메인으로, QR만으로 최종 목적지를 알기 어렵습니다.")

    if "@" in (norm or raw):
        lines.append("주소에 '@' 문자가 있어 다른 사이트로 숨겨진 링크일 수 있습니다.")

    pq = _path_query_text(norm or raw)
    if len(pq) > 80:
        lines.append("경로·쿼리가 매우 길어 임의 토큰·추적 파라미터가 많아 보입니다.")

    caution_kw = _find_keywords(pq, _CAUTION_PATH_KEYWORDS)
    if caution_kw:
        lines.append(
            "경로/쿼리에 민감 행위 연상 단어: "
            + ", ".join(caution_kw[:6])
            + (" …" if len(caution_kw) > 6 else "")
        )

    high_kw = _find_keywords(pq, _HIGH_RISK_PATH_KEYWORDS)
    if high_kw:
        lines.append(
            "경로에 고위험 연상 단어: " + ", ".join(high_kw)
        )

    parsed = urlparse(_ensure_scheme(norm or raw))
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=False)
        sensitive = [
            k for k in params if k.lower() in {"token", "password", "pass", "otp", "session", "redirect", "url", "next"}
        ]
        if sensitive:
            lines.append(
                "쿼리에 인증·리다이렉트 관련 파라미터가 포함되어 있습니다: "
                + ", ".join(sensitive[:5])
            )

    if final and final_host and host and final_host != host:
        lines.append(
            f"최종 도착 호스트({final_host})가 처음 호스트({host})와 다릅니다."
        )
        if req.hop_count:
            lines.append(f"중간 연결(리다이렉트) {req.hop_count}회 후 위 주소로 이어집니다.")

    if req.ml_phishing_probability_percent is not None:
        pct = req.ml_phishing_probability_percent
        if pct >= 70:
            lines.append(
                f"URL 패턴 ML 모델이 피싱과 유사하다고 {pct:.0f}% 수준으로 평가했습니다."
            )
        elif pct >= 40:
            lines.append(
                f"URL 패턴 ML 모델이 다소 의심스럽다고 {pct:.0f}% 수준으로 평가했습니다."
            )
        elif pct > 0:
            lines.append(
                f"URL 패턴 ML 모델 점수는 낮은 편입니다({pct:.0f}%)."
            )
        else:
            lines.append("URL 패턴 ML 모델 점수는 낮은 편입니다.")

    if not lines:
        lines.append("특이한 URL 구조 신호는 적습니다. 공식 주소와 일치하는지 확인이 필요합니다.")

    return lines
