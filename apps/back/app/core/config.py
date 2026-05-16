from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "QR Shield Back"
    app_version: str = "0.1.0"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    llm_base_url: str | None = Field(
        default=None,
        description="LLM service base URL, e.g. http://127.0.0.1:8001",
    )
    llm_enabled: bool = True
    llm_timeout_seconds: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QR_SHIELD_",
        extra="ignore",
    )


settings = Settings()

