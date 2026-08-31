from datetime import time
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.heat_risk import HeatRiskResponse
from app.schemas.surface_risk import SurfaceRiskResponse


class ActiveWalkStatusRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"]
    walk_time: time | None = None
    wait_seconds: int = Field(default=15, ge=1, le=20)


class ActiveWalkStatusResponse(BaseModel):
    heat_risk: HeatRiskResponse
    surface_risk: SurfaceRiskResponse
    recommended_duration_minutes: int = Field(ge=0)
    reminders: list[str]
    caution: str
    disclaimer: str
