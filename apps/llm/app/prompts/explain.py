# -*- coding: utf-8 -*-
from __future__ import annotations

from app.schemas.explain import ExplainRequest, RiskFactor

_LEVEL_KO = {"safe": "안전", "caution": "주의", "danger": "위험"}

# Gemini에 description을 넘기면 그 문장을 그대로 복사함 → type·점수만 전달
_FACTOR_KO = {
    "short_url": "단축 URL 도메인",
    "redirect": "리다이렉트",
    "excessive_redirect": "과다 리다이렉트",
    "domain_changed": "도메인 변경",
    "suspicious_tld": "의심 TLD",
    "ml_high_risk": "ML 고위험",
    "rule": "URL 규칙",
}


def _format_signals_compact(factors: list[RiskFactor]) -> str:
    if not factors:
        return "- (리다이렉트·단축 URL 등 자동 신호 없음)"
    lines: list[str] = []
    for f in factors:
        label = _FACTOR_KO.get(f.type, f.type)
        score = f"+{f.score}점" if f.score is not None else ""
        lines.append(f"- {label} {score}".strip())
    return "\n".join(lines)


def build_user_prompt(
    req: ExplainRequest,
    *,
    url_snapshot: str = "",
    url_insights: list[str] | None = None,
) -> str:
    display = req.grade_display or _LEVEL_KO.get(req.level, req.level)
    norm = req.normalized_url or req.url

    snapshot_block = url_snapshot or f"- URL: {req.url}"

    insights = url_insights or []
    insights_block = (
        "[URL 구조·패턴 분석]\n" + "\n".join(f"- {line}" for line in insights)
        if insights
        else "[URL 구조·패턴 분석]\n- (추가 힌트 없음)"
    )

    factors_lines = "[자동 탐지 신호 — 내부 코드만, 설명 문장 복사 금지]\n"
    factors_lines += _format_signals_compact(req.risk_factors)

    return f"""
[URL 주소 구조 — explanation의 첫 문장은 여기 호스트·경로를 직접 설명할 것]
{snapshot_block}

{insights_block}

{factors_lines}

[종합 판정]
- 위험 점수 (0~100): {req.score}
- 최종 판정: {display}

아래 JSON 형식으로만 응답하세요. 백틱 없이 순수 JSON만 출력하세요.

{{
  "explanation": "2~4문장. 초등 학생도 이해할 수 있는 쉬운 말. '~합니다' 종결어미.",
  "action_guide": ["행동1", "행동2", "행동3"]
}}

작성 규칙:
1. explanation 첫 문장: 반드시 [URL 주소 구조]의 호스트·경로·최종 URL을 사용자에게 풀어 설명 (예: "주소는 ○○.xyz이고 경로에 login이 들어 있습니다").
2. 둘째 문장: [URL 구조·패턴 분석]에서 1가지 이상 연결.
3. "단축 URL을 사용하고 있어…", "리다이렉트가 N회…" 같은 시스템 문구·탐지 신호 문장을 그대로 쓰지 마세요.
4. [자동 탐지 신호]는 이름만 참고하고, explanation에 항목 나열하지 마세요.
5. 근거는 위 블록만 사용. 운영자·유출·악성 단정 금지.
6. action_guide 2~3개 — URL 형태에 맞는 행동.

금지: 아래는 다른 URL 예시이므로 문장을 복사하지 마세요.
- "bit.ly", "example.xyz", "fake-naver" 등 예시 도메인
"""


EXPLAIN_SYSTEM = """당신은 QR코드 보안 분석 도우미입니다.
입력 URL의 호스트·경로·도메인 형태를 읽어 일반인에게 설명하는 것이 1순위입니다.
자동 탐지 신호(단축 URL, 리다이렉트 등)는 부가 정보이며, 그 설명 문장을 복사하지 마세요."""
