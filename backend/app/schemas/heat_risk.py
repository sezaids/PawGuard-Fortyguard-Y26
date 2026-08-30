from typing import Literal

from pydantic import BaseModel, Field


class CurrentRiskRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    wait_seconds: int = Field(default=15, ge=1, le=20)


class RiskFactor(BaseModel):
    factor: str
    points: int
    detail: str


class HeatRiskResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    status: Literal["Low", "Moderate", "High", "Very High"]
    recommendation: str
    main_factors: list[RiskFactor]
    environment: dict[str, float | None]
    disclaimer: str
