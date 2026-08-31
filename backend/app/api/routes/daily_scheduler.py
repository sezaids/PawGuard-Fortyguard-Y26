import logging
from datetime import UTC, datetime, timedelta
from threading import Lock, Thread
from time import perf_counter
from typing import Annotated
from uuid import uuid4

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
from app.services.fortyguard import FortyGuardError, fortyguard_service
from app.services.walk_planner import forecast_result_diagnostics, forecast_temperature_from_result

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
_SCHEDULE_TIMEOUT_SECONDS = 120
_schedule_analyses: dict[str, dict] = {}
_schedule_lock = Lock()
logger = logging.getLogger(__name__)


def _schedule_inputs(payload: DailyScheduleRequest, current_user: CurrentUser, db: Session) -> tuple[list[Dog], list[tuple[datetime, datetime]], list[datetime]]:
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
    return dogs, availability, forecast_times


def _set_failed(analysis_id: str, message: str) -> None:
    with _schedule_lock:
        analysis = _schedule_analyses.get(analysis_id)
        if analysis:
            analysis.update({"state": "failed", "stage": "failed", "message": message})


def _submit_forecast_jobs(analysis_id: str) -> None:
    """Submit provider jobs outside the browser request; the UI polls status."""
    with _schedule_lock:
        analysis = _schedule_analyses.get(analysis_id)
        if not analysis:
            return
        payload: DailyScheduleRequest = analysis["payload"]
        forecast_times: list[datetime] = analysis["forecast_times"]
    jobs: list[dict] = []
    try:
        for forecast_time in forecast_times:
            heatmap = HeatmapRequest(
                polygon_aoi=small_square_aoi(payload.latitude, payload.longitude),
                date_time=DateTimeFilter(start_date=forecast_time.date(), start_time=forecast_time.strftime("%H:%M"), filter_type=1),
                granularity=100,
                analytic_type="tcm",
            )
            submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload())
            activity_id = submitted.get("data", {}).get("activity_id")
            if not activity_id:
                raise HTTPException(status_code=502, detail="FortyGuard did not accept a forecast heatmap request.")
            jobs.append({"time": forecast_time, "activity_id": activity_id, "terminal": None, "result": None})
    except FortyGuardError as error:
        _set_failed(analysis_id, str(error.detail))
        return
    except HTTPException as error:
        _set_failed(analysis_id, str(error.detail))
        return
    with _schedule_lock:
        analysis = _schedule_analyses.get(analysis_id)
        if analysis:
            analysis.update({"state": "processing", "stage": "forecast", "jobs": jobs, "next_job_index": 0, "message": "Analyzing available forecast intervals…"})


def _analysis_for_user(analysis_id: str, current_user: CurrentUser) -> dict:
    with _schedule_lock:
        analysis = _schedule_analyses.get(analysis_id)
    if not analysis or analysis["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Daily schedule analysis was not found.")
    return analysis


@router.post("/analyses")
def start_daily_schedule_analysis(payload: DailyScheduleRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Start an asynchronous schedule forecast analysis without blocking the browser."""
    _, availability, forecast_times = _schedule_inputs(payload, current_user, db)
    analysis_id = str(uuid4())
    with _schedule_lock:
        _schedule_analyses[analysis_id] = {
            "owner_id": str(current_user.id),
            "payload": payload.model_copy(deep=True),
            "availability": availability,
            "forecast_times": forecast_times,
            "jobs": [],
            "state": "processing",
            "stage": "creating",
            "message": "Preparing forecast analysis…",
            "started": perf_counter(),
        }
    Thread(target=_submit_forecast_jobs, args=(analysis_id,), daemon=True).start()
    return {"state": "processing", "analysis_id": analysis_id, "stage": "creating", "message": "Preparing forecast analysis…"}


@router.get("/analyses/{analysis_id}")
def poll_daily_schedule_analysis(analysis_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """Poll one existing FortyGuard activity, then schedule from completed data."""
    analysis = _analysis_for_user(analysis_id, current_user)
    if analysis["state"] == "failed":
        return {"state": "failed", "analysis_id": analysis_id, "stage": analysis["stage"], "message": analysis["message"]}
    if perf_counter() - analysis["started"] >= _SCHEDULE_TIMEOUT_SECONDS:
        _set_failed(analysis_id, "FortyGuard did not complete the available forecast intervals within two minutes.")
        return {"state": "failed", "analysis_id": analysis_id, "stage": "timed_out", "message": "FortyGuard did not complete the available forecast intervals within two minutes."}
    if analysis["stage"] == "creating":
        return {"state": "processing", "analysis_id": analysis_id, "stage": "creating", "message": "Preparing forecast analysis…"}
    if analysis.get("result") is not None:
        return {"state": "completed", "analysis_id": analysis_id, "result": analysis["result"]}

    try:
        pending_jobs = [job for job in analysis["jobs"] if job["terminal"] is None]
        if pending_jobs:
            index = analysis.get("next_job_index", 0) % len(pending_jobs)
            job = pending_jobs[index]
            analysis["next_job_index"] = index + 1
            provider = fortyguard_service.status(job["activity_id"], timeout_seconds=8)
            data = provider.get("data", {})
            if data.get("status") == "Completed":
                job.update({"terminal": "completed", "result": data.get("result") or {}})
            elif data.get("status") == "Failed":
                job["terminal"] = "failed"
    except FortyGuardError as error:
        if error.status_code in {422, 429, 502, 503}:
            _set_failed(analysis_id, str(error.detail))
            return {"state": "failed", "analysis_id": analysis_id, "stage": "provider_error", "message": str(error.detail)}
        return {"state": "processing", "analysis_id": analysis_id, "stage": "forecast", "message": "FortyGuard is still processing the forecast. Retrying status shortly…"}

    if any(job["terminal"] is None for job in analysis["jobs"]):
        completed = sum(job["terminal"] == "completed" for job in analysis["jobs"])
        return {"state": "processing", "analysis_id": analysis_id, "stage": "forecast", "message": "Analyzing available forecast intervals…", "completed_intervals": completed, "total_intervals": len(analysis["jobs"])}

    intervals = []
    for job in analysis["jobs"]:
        if job["terminal"] != "completed":
            continue
        temperature = forecast_temperature_from_result(job["result"])
        if temperature is not None:
            intervals.append({"time": job["time"], "temperature_celsius": temperature})
    if not intervals:
        completed_results = [job["result"] for job in analysis["jobs"] if job["terminal"] == "completed"]
        logger.warning("FortyGuard Daily Scheduler completed without forecast temperatures; schema=%s", forecast_result_diagnostics(completed_results[0]) if completed_results else {})
        _set_failed(analysis_id, "FortyGuard completed without usable forecast data for this location.")
        return {"state": "failed", "analysis_id": analysis_id, "stage": "no_data", "message": "FortyGuard completed without usable forecast data for this location."}

    dogs = list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))
    result = build_daily_schedule(dogs, intervals, analysis["availability"], surface=analysis["payload"].surface)
    with _schedule_lock:
        analysis.update({"state": "completed", "stage": "completed", "result": result})
    return {"state": "completed", "analysis_id": analysis_id, "result": result}


@router.post("/daily", response_model=DailyScheduleResponse)
def schedule_daily_walks(payload: DailyScheduleRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Legacy synchronous endpoint retained for existing API clients."""
    dogs, availability, forecast_times = _schedule_inputs(payload, current_user, db)
    intervals = []
    for forecast_time in forecast_times:
        heatmap = HeatmapRequest(polygon_aoi=small_square_aoi(payload.latitude, payload.longitude), date_time=DateTimeFilter(start_date=forecast_time.date(), start_time=forecast_time.strftime("%H:%M"), filter_type=1), granularity=100, analytic_type="tcm")
        submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload())
        activity_id = submitted.get("data", {}).get("activity_id")
        if not activity_id:
            continue
        data = fortyguard_service.wait_for_completion(activity_id, max(1, payload.wait_seconds // len(forecast_times))).get("data", {})
        temperature = forecast_temperature_from_result(data.get("result") or {}) if data.get("status") == "Completed" else None
        if temperature is not None:
            intervals.append({"time": forecast_time, "temperature_celsius": temperature})
    if not intervals:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Forecast heatmap data is still processing or unavailable. Please try again shortly.")
    return build_daily_schedule(dogs, intervals, availability, surface=payload.surface)
