from dataclasses import dataclass
from enum import StrEnum


class RiskLevel(StrEnum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGER = "danger"


@dataclass(frozen=True)
class RiskSignal:
    label: str
    score: int

