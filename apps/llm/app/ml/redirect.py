# -*- coding: utf-8 -*-
from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx

_SHORT_HOSTS: frozenset[str] = frozenset(
    {"bit.ly", "t.co", "tinyurl.com", "goo.gl", "ow.ly", "short.io"}
)
_SUSPICIOUS_TLDS: tuple[str, ...] = (
    ".xyz",
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",
)
_REDIRECT_STATUSES: frozenset[int] = frozenset({301, 302, 303, 307, 308})


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
    if h.startswith("www."):
        return h[4:]
    return h


def _host_of(url: str) -> str:
    p = urlparse(url)
    return _strip_www(p.hostname)


def _is_short_url_host(host: str) -> bool:
    if not host:
        return False
    return _strip_www(host) in _SHORT_HOSTS


def _has_suspicious_tld(host: str | None) -> bool:
    if not host:
        return False
    h = host.lower()
    return any(h.endswith(tld) for tld in _SUSPICIOUS_TLDS)


async def trace_redirects(url: str, max_hops: int = 5) -> dict:
    original_url = url.strip()
    start = _ensure_scheme(original_url) if original_url else original_url
    original_host = _host_of(start)

    is_short = bool(original_host and _is_short_url_host(original_host))

    hop_count = 0
    current = start
    final_url = current

    timeout = httpx.Timeout(3.0)
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
        ) as client:
            visited: set[str] = set()
            for _ in range(max_hops + 1):
                if not current:
                    break
                if current in visited:
                    break
                visited.add(current)

                try:
                    resp = await client.head(current, follow_redirects=False)
                except httpx.RequestError:
                    break

                final_url = str(resp.url)

                code = resp.status_code
                if code in _REDIRECT_STATUSES and hop_count < max_hops:
                    loc = resp.headers.get("location")
                    if not loc:
                        break
                    current = urljoin(final_url, loc)
                    hop_count += 1
                    continue

                break

    except Exception:
        final_url = start if start else original_url

    final_host = _host_of(final_url)
    domain_changed = bool(original_host and final_host and original_host != final_host)

    return {
        "original_url": original_url,
        "final_url": final_url if final_url else start,
        "hop_count": hop_count,
        "domain_changed": domain_changed,
        "is_short_url": is_short,
        "suspicious_tld": _has_suspicious_tld(urlparse(final_url).hostname),
    }


def calculate_redirect_score(redirect_info: dict) -> tuple[int, list[dict]]:
    score = 0
    factors: list[dict] = []

    if redirect_info.get("is_short_url"):
        score += 20
        factors.append(
            {
                "type": "short_url",
                "description": "단축 URL을 사용하고 있어 실제 목적지를 바로 확인하기 어렵습니다.",
                "score": 20,
            }
        )

    hops = int(redirect_info.get("hop_count") or 0)
    if hops >= 3:
        score += 20
        factors.append(
            {
                "type": "excessive_redirect",
                "description": "리다이렉트가 3회 이상 이어져 연결 경로를 추적하기 어렵습니다.",
                "score": 20,
            }
        )
    elif hops in (1, 2):
        score += 10
        factors.append(
            {
                "type": "redirect",
                "description": f"주소가 {hops}회 다른 곳으로 연결(리다이렉트)되었습니다.",
                "score": 10,
            }
        )

    if redirect_info.get("domain_changed"):
        score += 15
        factors.append(
            {
                "type": "domain_changed",
                "description": "처음 도메인과 다른 도메인으로 이동한 흔적이 있습니다.",
                "score": 15,
            }
        )

    if redirect_info.get("suspicious_tld"):
        score += 20
        factors.append(
            {
                "type": "suspicious_tld",
                "description": "의심되는 최상위 도메인(TLD) 형태가 보입니다.",
                "score": 20,
            }
        )

    return score, factors
