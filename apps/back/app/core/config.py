from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "QR Shield Back"
    app_version: str = "0.1.0"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="QR_SHIELD_",
        extra="ignore",
    )


settings = Settings()

