from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RiskLevelValue = Literal["safe", "caution", "danger"]


class AnalyzeUrlRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("url must not be empty")
        return stripped


class ScanResultResponse(BaseModel):
    id: str
    url: str
    risk_level: RiskLevelValue = Field(..., alias="riskLevel")
    score: int = Field(..., ge=0, le=100)
    explanation: str
    action_guide: str = Field(..., alias="actionGuide")
    signals: list[str]
    scanned_at: datetime = Field(..., alias="scannedAt")

    model_config = ConfigDict(populate_by_name=True)

