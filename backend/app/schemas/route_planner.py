from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class RoutePoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RoutePlanRequest(BaseModel):
    start: RoutePoint
    destination: RoutePoint | None = None
    mode: Literal["destination", "loop"] = "destination"
    heat_wait_seconds: int = Field(default=15, ge=0, le=20)

    @model_validator(mode="after")
    def destination_or_loop(self) -> "RoutePlanRequest":
        if self.mode == "destination" and self.destination is None:
            raise ValueError("A destination is required when planning a point-to-point walk")
        return self


class RouteOption(BaseModel):
    id: str
    geometry: dict[str, Any]
    distance_meters: float
    duration_seconds: float
    estimated_walking_minutes: int
    relative_heat_exposure: int | None = Field(default=None, ge=0, le=100)
    heat_optimized: bool
    explanation: str


class RoutePlanResponse(BaseModel):
    recommended_route: RouteOption
    alternatives: list[RouteOption]
    heat_optimization_available: bool
    message: str
    heatmap: dict[str, Any] | None = None
    disclaimer: str
    heat_activity_id: str | None = None
