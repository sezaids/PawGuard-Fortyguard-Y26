from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.walk_planner import small_square_aoi
from app.core.daily_scheduler_rules import DAILY_SCHEDULER_RULES
from app.db.session import get_db
from app.models.dog import Dog
from app.schemas.daily_scheduler import DailyScheduleRequest, DailyScheduleResponse
from app.schemas.fortyguard import DateTimeFilter, HeatmapRequest
from app.services.daily_scheduler import build_daily_schedule
from app.services.fortyguard import fortyguard_service
from app.services.walk_planner import forecast_temperature_from_result

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/daily", response_model=DailyScheduleResponse)
def schedule_daily_walks(payload: DailyScheduleRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Create a conflict-free plan from only completed, in-horizon FortyGuard intervals."""
    dogs = list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))
    if not dogs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Add a dog before creating a daily schedule.")

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    horizon_end = now + timedelta(hours=DAILY_SCHEDULER_RULES.maximum_forecast_hours)
    availability = [(block.start.astimezone(UTC), block.end.astimezone(UTC)) for block in payload.availability]
    if any(start < now or end > horizon_end for start, end in availability):
        raise HTTPException(status_code=422, detail="Availability must be within FortyGuard’s real upcoming 12-hour forecast horizon.")

    forecast_times = [
        now + timedelta(hours=offset) for offset in range(DAILY_SCHEDULER_RULES.maximum_forecast_hours)
        if any(start <= now + timedelta(hours=offset) < end for start, end in availability)
    ]
    if not forecast_times:
        raise HTTPException(status_code=422, detail="No whole forecast intervals fall within the time blocks you supplied.")

    submissions: list[tuple[datetime, str]] = []
    for forecast_time in forecast_times:
        heatmap = HeatmapRequest(polygon_aoi=small_square_aoi(payload.latitude, payload.longitude), date_time=DateTimeFilter(start_date=forecast_time.date(), start_time=forecast_time.strftime("%H:%M"), filter_type=1), granularity=100, analytic_type="tcm")
        submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload())
        activity_id = submitted.get("data", {}).get("activity_id")
        if activity_id:
            submissions.append((forecast_time, activity_id))
    if not submissions:
        raise HTTPException(status_code=502, detail="FortyGuard did not accept forecast heatmap requests.")

    per_job_wait = max(1, payload.wait_seconds // len(submissions))
    intervals = []
    for forecast_time, activity_id in submissions:
        completed = fortyguard_service.wait_for_completion(activity_id, per_job_wait)
        data = completed.get("data", {})
        temperature = forecast_temperature_from_result(data.get("result") or {}) if data.get("status") == "Completed" else None
        if temperature is not None:
            intervals.append({"time": forecast_time, "temperature_celsius": temperature})
    if not intervals:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Forecast heatmap data is still processing or unavailable. Please try again shortly.")
    return build_daily_schedule(dogs, intervals, availability, surface=payload.surface)
