from typing import Any, Literal

from pydantic import BaseModel, Field


class HeatmapViewRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    wait_seconds: int = Field(default=20, ge=0, le=20)


class HeatmapViewResponse(BaseModel):
    state: Literal["processing", "completed", "failed", "no_data"]
    activity_id: str | None = None
    message: str
    map_data: dict[str, Any] | None = None
    stats_data: dict[str, Any] | None = None
