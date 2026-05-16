# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from typing import Any

from google import genai

from app.core.config import Settings, get_gemini_api_key
from app.prompts.explain import EXPLAIN_SYSTEM, build_user_prompt
from app.prompts.safety import build_safety_prompt
from app.schemas.explain import ExplainRequest, ExplainResponse


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    fence = re.match(
        r"^\s*```(?:json)?\s*(.*?)\s*```\s*$",
        text, re.DOTALL | re.IGNORECASE
    )
    return fence.group(1).strip() if fence else text


def _parse_llm_json(text: str) -> dict[str, Any]:
    return json.loads(_strip_json_fence(text))


def _apply_safety_review(
    client: genai.Client,
    model_name: str,
    draft: dict[str, Any],
) -> dict[str, Any]:
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=build_safety_prompt(draft),
        )
        raw = getattr(response, "text", None) or ""
        reviewed = _parse_llm_json(raw)
        explanation = str(reviewed.get("explanation", "")).strip()
        guides_raw = reviewed.get("action_guide", [])
        action_guide = (
            [guides_raw.strip()]
            if isinstance(guides_raw, str)
            else [str(x).strip() for x in guides_raw if str(x).strip()]
        )
        if explanation and action_guide:
            return {"explanation": explanation, "action_guide": action_guide}
    except Exception:
        pass
    return draft


def _fallback_response(req: ExplainRequest) -> tuple[str, list[str]]:
    factors = req.risk_factors
    factor_summary = (
        " (" + "; ".join(f.description for f in factors[:3]) + ")"
        if factors else ""
    )

    templates = {
        "safe": (
            "자동 분석 결과 위험 요소가 확인되지 않았습니다. "
            "공식 사이트 주소가 맞는지 한 번 더 확인 후 이용하세요.",
            [
                "주소가 공식 사이트와 일치하는지 확인하세요.",
                "개인정보 입력 전 주소창을 한 번 더 확인하세요.",
            ],
        ),
        "caution": (
            f"자동 분석에서 주의가 필요한 요소가 발견되었습니다{factor_summary}. "
            "공식 경로를 통해 해당 서비스를 직접 확인하시는 것이 좋습니다.",
            [
                "QR 링크로 바로 접속하지 마세요.",
                "공식 앱이나 포털에서 직접 검색해 확인하세요.",
                "로그인·결제·개인정보 입력 요구 시 즉시 이탈하세요.",
            ],
        ),
        "danger": (
            f"위험 요소가 여러 개 확인되었습니다{factor_summary}. "
            "개인정보나 금융정보를 입력했다면 즉시 조치가 필요합니다.",
            [
                "즉시 접속을 중단하세요.",
                "이미 정보를 입력했다면 비밀번호 변경 및 카드사에 연락하세요.",
                "공식 앱에서 직접 해당 서비스를 확인하세요.",
            ],
        ),
    }

    expl, guides = templates.get(req.level, templates["caution"])
    return expl, guides


def explain_with_gemini(
    settings: Settings, req: ExplainRequest
) -> ExplainResponse:
    api_key = get_gemini_api_key(settings)
    model_name = settings.gemini_model

    if not api_key:
        expl, guides = _fallback_response(req)
        return ExplainResponse(
            explanation=expl,
            action_guide=guides,
            used_llm=False,
            model=None,
        )

    client = genai.Client(api_key=api_key)
    full_prompt = EXPLAIN_SYSTEM + "\n\n" + build_user_prompt(req)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
        )
        raw = getattr(response, "text", None) or ""
        parsed = _parse_llm_json(raw)

        explanation = str(parsed.get("explanation", "")).strip()
        guides_raw = parsed.get("action_guide", [])
        action_guide = (
            [guides_raw.strip()] if isinstance(guides_raw, str)
            else [str(x).strip() for x in guides_raw if str(x).strip()]
        )

        if not explanation:
            expl, action_guide = _fallback_response(req)
            return ExplainResponse(
                explanation=expl,
                action_guide=action_guide,
                used_llm=False,
                model=model_name,
            )

        if not action_guide:
            _, action_guide = _fallback_response(req)

        reviewed = _apply_safety_review(
            client,
            model_name,
            {"explanation": explanation, "action_guide": action_guide},
        )
        explanation = str(reviewed.get("explanation", explanation)).strip()
        action_guide = reviewed.get("action_guide", action_guide)

        return ExplainResponse(
            explanation=explanation,
            action_guide=action_guide,
            used_llm=True,
            model=model_name,
        )

    except Exception:
        expl, guides = _fallback_response(req)
        return ExplainResponse(
            explanation=expl,
            action_guide=guides,
            used_llm=False,
            model=model_name,
        )