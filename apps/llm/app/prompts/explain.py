# -*- coding: utf-8 -*-
from __future__ import annotations
from app.schemas.explain import ExplainRequest

_LEVEL_KO = {"safe": "안전", "caution": "주의", "danger": "위험"}


def build_user_prompt(req: ExplainRequest) -> str:
    display = req.grade_display or _LEVEL_KO.get(req.level, req.level)
    norm = req.normalized_url or req.url

    if req.final_url is not None and req.hop_count is not None:
        hops = (
            f"- 원본 URL: {req.url}\n"
            f"- 최종 도착 URL: {req.final_url}\n"
            f"- 리다이렉트 횟수: {req.hop_count}회\n"
        )
    else:
        hops = f"- 확인된 URL: {norm}\n"

    ml_line = ""
    if req.ml_phishing_probability_percent is not None:
        ml_line = (
            f"- ML 모델 피싱 탐지 확률: "
            f"{req.ml_phishing_probability_percent:.1f}%\n"
        )

    factors_lines = ""
    if req.risk_factors:
        factors_lines = "[탐지된 위험 요소]\n" + "\n".join(
            f"- {f.type}: {f.description}"
            + (f" (가중치 {f.score})" if f.score is not None else "")
            for f in req.risk_factors
        )
    else:
        factors_lines = "[탐지된 위험 요소 없음]"
        if req.ml_phishing_probability_percent is not None and (
            req.ml_phishing_probability_percent >= 70
        ):
            factors_lines += (
                "\n- (ML 모델만 높은 점수: 위 ML 확률을 설명의 근거로 반영하세요.)"
            )

    return f"""
[자동 분석 결과]
{hops}{ml_line}- 위험 점수 (0~100): {req.score}
- 최종 판정: {display}

{factors_lines}

아래 JSON 형식으로만 응답하세요. 백틱 없이 순수 JSON만 출력하세요.

{{
  "explanation": "2~3문장. 일반 시민이 이해할 수 있는 쉬운 말. '~합니다' 종결어미.",
  "action_guide": ["행동1", "행동2", "행동3"]
}}

주의사항:
- [자동 분석 결과]만 참고하고 추측 금지
- '100% 안전', '절대 안전' 같은 단정 표현 금지
- 공포·불안 조장 금지
- 개인정보 추측 출력 금지
- action_guide는 반드시 리스트 형태로 2~3개
"""


EXPLAIN_SYSTEM = """당신은 QR코드 보안 분석 도우미입니다.
QR코드로 연결되는 URL의 위험도를 이미 시스템이 분석했습니다.
그 결과를 바탕으로 고령층도 이해할 수 있는 쉬운 한국어로
위험 이유와 행동 지침을 안내해주세요."""