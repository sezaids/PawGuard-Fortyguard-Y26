from datetime import time
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.heat_risk import CurrentRiskRequest, RiskFactor


class SurfaceRiskRequest(CurrentRiskRequest):
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"]
    walk_time: time | None = Field(default=None, description="Local planned walk time; defaults to current UTC time when omitted")


class SurfaceRiskResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    level: Literal["Low", "Moderate", "High", "Very High"]
    surface: str
    reason: str
    main_factors: list[RiskFactor]
    safer_alternatives: list[str]
    environment: dict[str, float | None]
    disclaimer: str
