# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.explain_router import router as explain_router
from app.core.config import Settings, get_gemini_api_key

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
    return {
        "status": "ok",
        "gemini_configured": bool(get_gemini_api_key(settings)),
        "model": settings.gemini_model,
        "service": "llm",
    }

app.include_router(explain_router)
