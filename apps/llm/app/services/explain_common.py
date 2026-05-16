# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any

from app.prompts.explain import EXPLAIN_SYSTEM, build_user_prompt
from app.schemas.explain import ExplainRequest
from app.services.url_insights import build_url_insights, build_url_snapshot


def strip_json_fence(raw: str) -> str:
    text = raw.strip()
    fence = re.match(
        r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    return fence.group(1).strip() if fence else text


def parse_llm_json(text: str) -> dict[str, Any]:
    return json.loads(strip_json_fence(text))


def build_explain_prompt(req: ExplainRequest) -> str:
    snapshot = build_url_snapshot(req)
    insights = build_url_insights(req)
    return EXPLAIN_SYSTEM + "\n\n" + build_user_prompt(
        req,
        url_snapshot=snapshot,
        url_insights=insights,
    )


def url_hint_sentence(req: ExplainRequest) -> str:
    insights = build_url_insights(req)
    if not insights:
        return ""
    return " ".join(i.rstrip(".") for i in insights[:3]) + "."


def fallback_response(req: ExplainRequest) -> tuple[str, list[str]]:
    url_hint = url_hint_sentence(req)
    host_line = url_hint or "주소 형태를 한 번 더 확인해 주세요."

    templates = {
        "safe": (
            f"{host_line} 자동 분석상 뚜렷한 위험 신호는 적습니다. "
            "그래도 QR·문자로 받은 링크라면 공식 앱·포털 주소와 일치하는지 확인 후 이용하세요.",
            [
                "주소가 공식 사이트와 일치하는지 확인하세요.",
                "개인정보 입력 전 주소창을 한 번 더 확인하세요.",
            ],
        ),
        "caution": (
            f"{host_line} URL 형태나 연결 방식상 주의가 필요합니다. "
            "QR로 바로 열기보다 공식 경로에서 같은 서비스를 직접 찾아보세요.",
            [
                "QR 링크로 바로 접속하지 마세요.",
                "공식 앱이나 포털에서 직접 검색해 확인하세요.",
                "로그인·결제·개인정보 입력 요구 시 즉시 이탈하세요.",
            ],
        ),
        "danger": (
            f"{host_line} 여러 신호가 겹쳐 위험한 연결 패턴으로 보입니다. "
            "접속을 중단하고, 이미 정보를 입력했다면 비밀번호 변경 등 즉시 조치하세요.",
            [
                "즉시 접속을 중단하세요.",
                "이미 정보를 입력했다면 비밀번호 변경 및 카드사에 연락하세요.",
                "공식 앱에서 직접 해당 서비스를 확인하세요.",
            ],
        ),
    }

    expl, guides = templates.get(req.level, templates["caution"])
    return expl, guides


def parse_explain_payload(raw: str) -> tuple[str, list[str]]:
    parsed = parse_llm_json(raw)
    explanation = str(parsed.get("explanation", "")).strip()
    guides_raw = parsed.get("action_guide", [])
    action_guide = (
        [guides_raw.strip()]
        if isinstance(guides_raw, str)
        else [str(x).strip() for x in guides_raw if str(x).strip()]
    )
    return explanation, action_guide
