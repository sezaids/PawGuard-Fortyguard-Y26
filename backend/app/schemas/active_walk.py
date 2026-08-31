from datetime import time
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.heat_risk import HeatRiskResponse
from app.schemas.surface_risk import SurfaceRiskResponse


class ActiveWalkStatusRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"]
    walk_time: time | None = None
    wait_seconds: int = Field(default=15, ge=1, le=20)


class ActiveWalkStatusResponse(BaseModel):
    """A complete live status or an explicit no-live-data result.

    The unavailable shape deliberately contains no substitute weather or risk
    values. It lets clients keep the walk screen usable when FortyGuard is
    delayed without presenting an estimate as current.
    """

    state: Literal["available", "unavailable"] = "available"
    heat_risk: HeatRiskResponse | None = None
    surface_risk: SurfaceRiskResponse | None = None
    recommended_duration_minutes: int | None = Field(default=None, ge=0)
    reminders: list[str]
    caution: str
    disclaimer: str
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def validate_live_status_fields(self) -> "ActiveWalkStatusResponse":
        live_fields = (self.heat_risk, self.surface_risk, self.recommended_duration_minutes)
        if self.state == "available" and any(field is None for field in live_fields):
            raise ValueError("available Active Walk status requires complete risk and duration data")
        if self.state == "unavailable" and any(field is not None for field in live_fields):
            raise ValueError("unavailable Active Walk status cannot include live risk or duration data")
        if self.state == "unavailable" and not self.unavailable_reason:
            raise ValueError("unavailable Active Walk status requires an unavailable reason")
        return self
