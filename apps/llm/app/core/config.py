# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash-lite"
    upstage_api_key: str | None = None
    solar_model: str = "solar-pro2"
    solar_temperature: float = 0.65
    llm_timeout_seconds: float = 60.0
    # auto | solar | gemini — auto: .env 있으면 Solar 키 우선
    llm_provider: str = "auto"
    cors_origins: str = "*"  # 콤마로 구분. MVP에서는 * 허용, 운영 시 제한 권장

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def get_gemini_api_key(settings: Settings) -> str | None:
    """GEMINI_API_KEY 우선, 없으면 google-genai가 쓰는 GOOGLE_API_KEY."""
    import os

    key = settings.gemini_api_key or os.environ.get("GOOGLE_API_KEY")
    if key and str(key).strip():
        return str(key).strip()
    return None


def get_upstage_api_key(settings: Settings) -> str | None:
    """UPSTAGE_API_KEY (Upstage Console)."""
    import os

    key = settings.upstage_api_key or os.environ.get("UPSTAGE_API_KEY")
    if key and str(key).strip():
        return str(key).strip()
    return None
