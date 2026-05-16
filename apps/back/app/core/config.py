from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "QR Shield Back"
    app_version: str = "0.1.0"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    llm_enabled: bool = False
    llm_base_url: str = "http://localhost:8001"
    llm_timeout_seconds: float = 3.0
    llm_ml_score_weight: float = Field(default=0.4, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QR_SHIELD_",
        extra="ignore",
    )


settings = Settings()
