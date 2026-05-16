# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any


SAFETY_SYSTEM = """당신은 QR 보안 안내 문구 검수자입니다.
입력 JSON의 explanation과 action_guide만 검토합니다.

수정 규칙:
- "100% 안전", "절대 안전", "반드시 악성" 같은 단정 표현 제거
- 공포·불안 조장 문구 완화
- 입력에 없는 사실·개인정보 추측 제거
- 원본 프롬프트의 URL·도메인·경로 형태에 대한 설명은 유지 (임의로 삭제하지 않음)
- 의미는 유지하되 2~3문장, 쉬운 한국어 유지
- action_guide는 2~3개 짧은 문장 리스트

동일 JSON 스키마로만 응답하세요. 백틱 없이 순수 JSON만 출력하세요.
"""


def build_safety_prompt(draft: dict[str, Any]) -> str:
    payload = json.dumps(
        {
            "explanation": draft.get("explanation", ""),
            "action_guide": draft.get("action_guide", []),
        },
        ensure_ascii=False,
    )
    return f"{SAFETY_SYSTEM}\n\n검수할 JSON:\n{payload}"
