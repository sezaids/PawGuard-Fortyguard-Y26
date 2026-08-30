from datetime import time
from typing import Literal

from pydantic import BaseModel, Field


class WalkMatchRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    available_minutes: Literal[15, 30, 45, 60]
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"] | None = None
    walk_time: time | None = None
    wait_seconds: int = Field(default=15, ge=1, le=20)


class WalkMatchItem(BaseModel):
    dog_id: str
    dog_name: str
    estimated_risk: int = Field(ge=0, le=100)
    status: Literal["Low", "Moderate", "High", "Very High"]
    recommended_duration_minutes: int = Field(ge=0)
    duration_cap_minutes: int = Field(ge=0)
    suitable: bool
    why: str
    main_factors: list[dict]
    heat_risk: dict
    surface_risk: dict | None


class WalkMatchResponse(BaseModel):
    best_match: WalkMatchItem | None
    ranked_matches: list[WalkMatchItem]
    avoid: list[WalkMatchItem]
    message: str
    disclaimer: str
