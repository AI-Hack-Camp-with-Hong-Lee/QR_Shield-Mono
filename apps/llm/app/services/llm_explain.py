# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from app.core.config import Settings, get_gemini_api_key, get_upstage_api_key
from app.schemas.explain import ExplainRequest, ExplainResponse, LlmProviderLiteral
from app.services.gemini_service import explain_with_gemini
from app.services.solar_service import explain_with_solar

logger = logging.getLogger(__name__)

ExplainBackend = Literal["solar", "gemini", "fallback"]


def llm_dotenv_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def dotenv_exists() -> bool:
    return llm_dotenv_path().is_file()


def _tag(resp: ExplainResponse, provider: LlmProviderLiteral) -> ExplainResponse:
    return resp.model_copy(update={"llm_provider": provider})


def resolve_explain_backend(settings: Settings) -> ExplainBackend:
    pref = (settings.llm_provider or "auto").strip().lower()
    if pref == "gemini":
        return "gemini" if get_gemini_api_key(settings) else "fallback"
    if pref == "solar":
        return "solar" if get_upstage_api_key(settings) else "fallback"

    if dotenv_exists():
        if get_upstage_api_key(settings):
            return "solar"
        if get_gemini_api_key(settings):
            return "gemini"
        return "fallback"
    if get_upstage_api_key(settings):
        return "solar"
    if get_gemini_api_key(settings):
        return "gemini"
    return "fallback"


def _try_solar(settings: Settings, req: ExplainRequest) -> ExplainResponse | None:
    if not get_upstage_api_key(settings):
        return None
    try:
        resp = explain_with_solar(settings, req)
        provider: LlmProviderLiteral = "solar" if resp.used_llm else "template"
        logger.info(
            "explain solar used_llm=%s model=%s url=%s",
            resp.used_llm,
            resp.model,
            req.url[:80],
        )
        return _tag(resp, provider)
    except Exception as exc:
        logger.warning("Solar explain failed (%s); try next backend", exc)
        return None


def _run_gemini(settings: Settings, req: ExplainRequest) -> ExplainResponse:
    resp = explain_with_gemini(settings, req)
    provider: LlmProviderLiteral = "gemini" if resp.used_llm else "template"
    logger.info(
        "explain gemini used_llm=%s model=%s url=%s",
        resp.used_llm,
        resp.model,
        req.url[:80],
    )
    return _tag(resp, provider)


def explain_with_llm(settings: Settings, req: ExplainRequest) -> ExplainResponse:
    pref = (settings.llm_provider or "auto").strip().lower()

    if pref == "gemini":
        return _run_gemini(settings, req)

    if pref == "solar":
        solar_resp = _try_solar(settings, req)
        if solar_resp is not None:
            return solar_resp
        return _run_gemini(settings, req)

    # auto: Solar 우선 → 실패 시 Gemini
    solar_resp = _try_solar(settings, req)
    if solar_resp is not None and solar_resp.used_llm:
        return solar_resp
    if solar_resp is not None and not solar_resp.used_llm:
        # 키는 있는데 파싱 실패 등 → Gemini 재시도
        gemini_resp = _run_gemini(settings, req)
        if gemini_resp.used_llm:
            return gemini_resp
        return solar_resp

    return _run_gemini(settings, req)
