from typing import Literal

from pydantic import BaseModel, Field


class WalkPlanRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"] | None = None
    horizon_hours: int = Field(default=12, ge=1, le=12)
    interval_hours: Literal[1, 2, 3] = 3
    wait_seconds: int = Field(default=20, ge=1, le=20)


class WalkWindow(BaseModel):
    start: str
    forecast_temperature_celsius: float
    estimated_risk: int = Field(ge=0, le=100)
    status: Literal["Low", "Moderate", "High", "Very High"]
    recommended_duration_minutes: int = Field(ge=0)
    heat_risk: dict
    surface_risk: dict | None
    explanation: str


class WalkPlanResponse(BaseModel):
    best_window: WalkWindow | None
    alternatives: list[WalkWindow]
    all_windows: list[WalkWindow]
    message: str
    disclaimer: str
