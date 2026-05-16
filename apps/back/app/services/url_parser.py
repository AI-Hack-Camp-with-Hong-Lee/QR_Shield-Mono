from __future__ import annotations

import re
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import ParseResult, urlparse


_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


@dataclass(frozen=True)
class ParsedUrl:
    original: str
    normalized: str
    parsed: ParseResult
    hostname: str
    is_valid_web_url: bool
    validation_signal: str | None = None

    @property
    def scheme(self) -> str:
        return self.parsed.scheme.lower()

    @property
    def path_and_query(self) -> str:
        query = f"?{self.parsed.query}" if self.parsed.query else ""
        return f"{self.parsed.path}{query}"


def parse_url(value: str) -> ParsedUrl:
    candidate = value.strip()
    parsed = urlparse(candidate)

    if not parsed.scheme and looks_like_web_url_without_scheme(candidate):
        candidate = f"https://{candidate}"
        parsed = urlparse(candidate)

    hostname = (parsed.hostname or "").lower()
    validation_signal = None
    is_valid = True

    if parsed.scheme not in {"http", "https"}:
        is_valid = False
        validation_signal = "HTTP/HTTPS URL이 아님"
    elif not hostname:
        is_valid = False
        validation_signal = "호스트 정보 없음"
    elif not (looks_like_domain(hostname) or is_ip_address(hostname)):
        is_valid = False
        validation_signal = "유효하지 않은 도메인 형식"

    return ParsedUrl(
        original=value,
        normalized=candidate,
        parsed=parsed,
        hostname=hostname,
        is_valid_web_url=is_valid,
        validation_signal=validation_signal,
    )


def looks_like_domain(value: str) -> bool:
    if "/" in value or " " in value:
        return False
    return bool(_DOMAIN_RE.match(value.rstrip(".")))


def looks_like_web_url_without_scheme(value: str) -> bool:
    if " " in value:
        return False

    host = value.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if not host:
        return False
    return looks_like_domain(host) or is_ip_address(host)


def is_ip_address(value: str) -> bool:
    try:
        ip_address(value)
    except ValueError:
        return False
    return True
