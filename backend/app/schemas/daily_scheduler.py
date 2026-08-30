from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AvailabilityBlock(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def valid_range(self) -> "AvailabilityBlock":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Availability block times must include a timezone")
        if self.end <= self.start:
            raise ValueError("Availability block end must be after its start")
        return self


class DailyScheduleRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    availability: list[AvailabilityBlock] = Field(min_length=1, max_length=8)
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"] | None = None
    wait_seconds: int = Field(default=20, ge=1, le=20)


class ScheduledWalk(BaseModel):
    dog_id: str
    dog_name: str
    start: str
    end: str
    duration_minutes: int = Field(ge=0)
    estimated_risk: int = Field(ge=0, le=100)
    status: Literal["Low", "Moderate", "High", "Very High"]
    forecast_temperature_celsius: float
    explanation: str
    heat_risk: dict
    surface_risk: dict | None


class UnscheduledDog(BaseModel):
    dog_id: str
    dog_name: str
    reason: str


class DailyScheduleResponse(BaseModel):
    scheduled: list[ScheduledWalk]
    unscheduled: list[UnscheduledDog]
    message: str
    disclaimer: str
