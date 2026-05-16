# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Any

from google import genai

logger = logging.getLogger(__name__)

from app.core.config import Settings, get_gemini_api_key
from app.prompts.safety import build_safety_prompt
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.services.explain_common import (
    build_explain_prompt,
    fallback_response,
    parse_explain_payload,
    parse_llm_json,
)


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
        reviewed = parse_llm_json(raw)
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


def explain_with_gemini(
    settings: Settings, req: ExplainRequest
) -> ExplainResponse:
    api_key = get_gemini_api_key(settings)
    model_name = settings.gemini_model

    if not api_key:
        expl, guides = fallback_response(req)
        return ExplainResponse(
            explanation=expl,
            action_guide=guides,
            used_llm=False,
            model=None,
        )

    client = genai.Client(api_key=api_key)
    full_prompt = build_explain_prompt(req)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
        )
        raw = getattr(response, "text", None) or ""
        explanation, action_guide = parse_explain_payload(raw)

        if not explanation:
            expl, action_guide = fallback_response(req)
            return ExplainResponse(
                explanation=expl,
                action_guide=action_guide,
                used_llm=False,
                model=model_name,
            )

        if not action_guide:
            _, action_guide = fallback_response(req)

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

    except Exception as exc:
        logger.warning("Gemini explain failed: %s", exc)
        expl, guides = fallback_response(req)
        return ExplainResponse(
            explanation=expl,
            action_guide=guides,
            used_llm=False,
            model=model_name,
        )
