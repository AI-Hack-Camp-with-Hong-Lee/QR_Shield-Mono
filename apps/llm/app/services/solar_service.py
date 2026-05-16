# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

import httpx

from app.core.config import Settings, get_upstage_api_key
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.services.explain_common import fallback_response, parse_explain_payload

logger = logging.getLogger(__name__)

UPSTAGE_CHAT_URL = "https://api.upstage.ai/v1/chat/completions"


def explain_with_solar(settings: Settings, req: ExplainRequest) -> ExplainResponse:
    api_key = get_upstage_api_key(settings)
    model_name = settings.solar_model

    if not api_key:
        expl, guides = fallback_response(req)
        return ExplainResponse(
            explanation=expl,
            action_guide=guides,
            used_llm=False,
            model=None,
        )

    from app.prompts.explain import EXPLAIN_SYSTEM, build_user_prompt
    from app.services.url_insights import build_url_insights, build_url_snapshot

    user_content = build_user_prompt(
        req,
        url_snapshot=build_url_snapshot(req),
        url_insights=build_url_insights(req),
    )
    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": EXPLAIN_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        "temperature": settings.solar_temperature,
        "top_p": 0.9,
    }

    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            resp = client.post(
                UPSTAGE_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        raw = ""
        choices = data.get("choices") or []
        if choices:
            raw = (choices[0].get("message") or {}).get("content") or ""
        if not raw:
            raise ValueError("empty solar response")

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

        return ExplainResponse(
            explanation=explanation,
            action_guide=action_guide,
            used_llm=True,
            model=model_name,
        )
    except Exception as exc:
        logger.warning("Upstage Solar explain failed: %s", exc)
        raise
