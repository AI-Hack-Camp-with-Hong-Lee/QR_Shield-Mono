from fastapi import APIRouter

from app.api.routes import analyze, health


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(analyze.router, prefix="/api/v1", tags=["analysis"])

