from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DateTimeFilter(BaseModel):
    start_date: date
    filter_type: Literal[1, 2, 3, 4]
    start_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end_date: date | None = None

    @model_validator(mode="after")
    def required_times(self) -> "DateTimeFilter":
        if self.filter_type in (1, 2) and not self.start_time:
            raise ValueError("start_time is required for a single hour or range of hours")
        if self.filter_type == 2 and not self.end_time:
            raise ValueError("end_time is required for a range of hours")
        if self.filter_type == 4 and not self.end_date:
            raise ValueError("end_date is required for a range of days")
        return self

    def provider_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class CurrentConditionsRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    wait_seconds: int = Field(default=0, ge=0, le=20)

    def provider_payload(self, temperature: float) -> dict[str, Any]:
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return {"latitude": self.latitude, "longitude": self.longitude, "temperature": temperature, "date_time": {"start_date": now.date().isoformat(), "start_time": now.strftime("%H:%M"), "filter_type": 1}}


class HeatmapRequest(BaseModel):
    polygon_aoi: dict[str, Any]
    date_time: DateTimeFilter
    granularity: Literal[60, 80, 100]
    analytic_type: Literal["tcm", "time_of_measure", "exceedance", "persistence"] = "tcm"
    threshold: float | None = None
    direction: Literal["above", "below"] | None = None
    wait_seconds: int = Field(default=0, ge=0, le=20)

    @model_validator(mode="after")
    def forecast_window(self) -> "HeatmapRequest":
        start = datetime.combine(self.date_time.start_date, datetime.min.time(), tzinfo=UTC)
        if self.date_time.start_time:
            start = start.replace(hour=int(self.date_time.start_time[:2]), minute=int(self.date_time.start_time[3:]))
        if start > datetime.now(UTC) + timedelta(hours=12):
            raise ValueError("FortyGuard heatmaps support at most 12 hours into the future")
        return self

    def provider_payload(self) -> dict[str, Any]:
        return {key: value for key, value in {"polygon_aoi": self.polygon_aoi, "date_time": self.date_time.provider_payload(), "granularity": self.granularity, "analytic_type": self.analytic_type, "threshold": self.threshold, "direction": self.direction}.items() if value is not None}


class ActivityResponse(BaseModel):
    error: bool
    status_code: int
    message: str
    data: dict[str, Any]
