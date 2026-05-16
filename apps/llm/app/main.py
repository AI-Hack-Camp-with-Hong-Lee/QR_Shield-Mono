# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.explain_router import router as explain_router
from app.core.config import Settings, get_gemini_api_key, get_upstage_api_key
from app.services.llm_explain import dotenv_exists, resolve_explain_backend

settings = Settings()

app = FastAPI(title="QR Shield LLM", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def api_health():
    backend = resolve_explain_backend(settings)
    active_model = (
        settings.solar_model
        if backend == "solar"
        else settings.gemini_model
        if backend == "gemini"
        else None
    )
    return {
        "status": "ok",
        "service": "llm",
        "dotenv_present": dotenv_exists(),
        "llm_provider_setting": settings.llm_provider,
        "explain_backend": backend,
        "solar_configured": bool(get_upstage_api_key(settings)),
        "solar_model": settings.solar_model,
        "gemini_configured": bool(get_gemini_api_key(settings)),
        "gemini_model": settings.gemini_model,
        "active_model": active_model,
        "model": active_model or settings.gemini_model,
    }

app.include_router(explain_router)
