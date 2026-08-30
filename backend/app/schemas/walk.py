from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


RiskStatus = Literal["Low", "Moderate", "High", "Very High"]
Surface = Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"]


class WalkCreate(BaseModel):
    dog_id: UUID
    completed_at: datetime | None = None
    duration_minutes: int = Field(ge=1, le=1440)
    surface: Surface
    heat_risk_score: int | None = Field(default=None, ge=0, le=100)
    heat_risk_status: RiskStatus | None = None
    surface_risk_score: int | None = Field(default=None, ge=0, le=100)
    surface_risk_status: RiskStatus | None = None
    route_distance_meters: int | None = Field(default=None, ge=0)
    route_duration_seconds: int | None = Field(default=None, ge=0)
    route_metadata: dict[str, Any] | None = None


class WalkResponse(WalkCreate):
    id: UUID
    dog_id: UUID | None
    dog_name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class WalkHistorySummary(BaseModel):
    total_walks: int
    total_minutes: int
    average_duration_minutes: int
    latest_walk: WalkResponse | None
    latest_heat_risk_status: RiskStatus | None
    message: str
