from datetime import UTC, datetime, timedelta
from threading import Lock, Thread
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.schemas.fortyguard import DateTimeFilter, HeatmapRequest
from app.schemas.walk_planner import WalkPlanRequest, WalkPlanResponse
from app.services.fortyguard import FortyGuardError, fortyguard_service
from app.services.walk_planner import forecast_temperature_from_result, rank_walk_windows

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]

# Short-lived in-process bridge between the browser and FortyGuard activities.
# It contains no secret and every poll is re-authorized against the signed-in user.
_forecast_analyses: dict[str, dict] = {}
_forecast_lock = Lock()


def small_square_aoi(latitude: float, longitude: float) -> dict:
    """A small closed GeoJSON polygon around the selected point for a heatmap request."""
    delta = 0.002
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[longitude - delta, latitude - delta], [longitude + delta, latitude - delta], [longitude + delta, latitude + delta], [longitude - delta, latitude + delta], [longitude - delta, latitude - delta]]]}}]}


def _set_failed(analysis_id: str, message: str) -> None:
    with _forecast_lock:
        analysis = _forecast_analyses.get(analysis_id)
        if analysis:
            analysis.update({"state": "failed", "message": message, "stage": "failed"})


def _submit_forecast_jobs(analysis_id: str) -> None:
    """Create provider jobs off the browser request path; polls happen through GET."""
    with _forecast_lock:
        analysis = _forecast_analyses.get(analysis_id)
        if not analysis:
            return
        payload: WalkPlanRequest = analysis["payload"]
        forecast_times: list[datetime] = analysis["forecast_times"]

    started = perf_counter()
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
        _set_failed(analysis_id, error.detail)
        return
    except HTTPException as error:
        _set_failed(analysis_id, str(error.detail))
        return

    with _forecast_lock:
        analysis = _forecast_analyses.get(analysis_id)
        if analysis:
            analysis.update({
                "stage": "forecast",
                "jobs": jobs,
                "next_job_index": 0,
                "creation_ms": round((perf_counter() - started) * 1000),
                "message": "Analyzing the next 12 hours…",
            })


def _analysis_for_user(analysis_id: str, current_user: CurrentUser) -> dict:
    with _forecast_lock:
        analysis = _forecast_analyses.get(analysis_id)
    if not analysis or analysis["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Walk Planner analysis was not found.")
    return analysis


@router.post("/dogs/{dog_id}/forecast-analyses")
def start_forecast_analysis(dog_id: UUID, payload: WalkPlanRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Start a non-blocking FortyGuard forecast analysis for the Walk Planner."""
    owned_dog(dog_id, current_user.id, db)
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    forecast_times = [now + timedelta(hours=offset) for offset in range(0, payload.horizon_hours, payload.interval_hours)]
    analysis_id = str(uuid4())
    with _forecast_lock:
        _forecast_analyses[analysis_id] = {
            "owner_id": str(current_user.id),
            "dog_id": dog_id,
            "payload": payload.model_copy(deep=True),
            "forecast_times": forecast_times,
            "jobs": [],
            "stage": "creating",
            "state": "processing",
            "message": "Preparing forecast analysis…",
            "started": perf_counter(),
        }
    Thread(target=_submit_forecast_jobs, args=(analysis_id,), daemon=True).start()
    return {"state": "processing", "analysis_id": analysis_id, "stage": "creating", "message": "Preparing forecast analysis…"}


@router.get("/forecast-analyses/{analysis_id}")
def poll_forecast_analysis(analysis_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """Poll short provider status calls and rank real data once every job is terminal."""
    analysis = _analysis_for_user(analysis_id, current_user)
    if analysis["state"] == "failed":
        return {"state": "failed", "analysis_id": analysis_id, "stage": "failed", "message": analysis["message"]}
    if analysis["stage"] == "creating":
        return {"state": "processing", "analysis_id": analysis_id, "stage": "creating", "message": "Preparing forecast analysis…"}
    if analysis.get("result") is not None:
        return {"state": "completed", "analysis_id": analysis_id, "result": analysis["result"], "timings_ms": analysis["timings_ms"]}

    poll_started = perf_counter()
    try:
        pending_jobs = [job for job in analysis["jobs"] if job["terminal"] is None]
        if pending_jobs:
            index = analysis.get("next_job_index", 0) % len(pending_jobs)
            job = pending_jobs[index]
            analysis["next_job_index"] = index + 1
            provider = fortyguard_service.status(job["activity_id"])
            provider_data = provider.get("data", {})
            provider_status = provider_data.get("status")
            if provider_status == "Completed":
                job["terminal"] = "completed"
                job["result"] = provider_data.get("result") or {}
            elif provider_status == "Failed":
                job["terminal"] = "failed"
    except FortyGuardError as error:
        if error.status_code in {422, 429, 502, 503}:
            _set_failed(analysis_id, error.detail)
            return {"state": "failed", "analysis_id": analysis_id, "stage": "provider_error", "message": error.detail}
        return {"state": "processing", "analysis_id": analysis_id, "stage": "forecast", "message": "FortyGuard is still processing the forecast. Retrying status shortly…", "provider_notice": error.detail}
    finally:
        analysis["polling_ms"] = analysis.get("polling_ms", 0) + round((perf_counter() - poll_started) * 1000)

    pending = sum(job["terminal"] is None for job in analysis["jobs"])
    if pending:
        completed = sum(job["terminal"] == "completed" for job in analysis["jobs"])
        return {"state": "processing", "analysis_id": analysis_id, "stage": "forecast", "message": "Analyzing the next 12 hours…", "completed_intervals": completed, "total_intervals": len(analysis["jobs"])}

    intervals = []
    for job in analysis["jobs"]:
        if job["terminal"] != "completed":
            continue
        temperature = forecast_temperature_from_result(job["result"])
        if temperature is not None:
            intervals.append({"time": job["time"], "temperature_celsius": temperature})
    if not intervals:
        _set_failed(analysis_id, "FortyGuard completed without usable forecast data for this location.")
        return {"state": "failed", "analysis_id": analysis_id, "stage": "no_data", "message": "FortyGuard completed without usable forecast data for this location."}

    ranking_started = perf_counter()
    dog = owned_dog(analysis["dog_id"], current_user.id, db)
    result = rank_walk_windows(dog, intervals, analysis["payload"].surface)
    timings = {
        "forecast_job_creation": analysis.get("creation_ms", 0),
        "provider_status_polling": analysis.get("polling_ms", 0),
        "ranking": round((perf_counter() - ranking_started) * 1000),
        "total": round((perf_counter() - analysis["started"]) * 1000),
    }
    with _forecast_lock:
        analysis.update({"result": result, "timings_ms": timings, "state": "completed", "stage": "completed"})
    return {"state": "completed", "analysis_id": analysis_id, "result": result, "timings_ms": timings}


@router.post("/dogs/{dog_id}/forecast", response_model=WalkPlanResponse)
def find_best_walk_time(dog_id: UUID, payload: WalkPlanRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Legacy synchronous endpoint retained for existing API clients."""
    dog = owned_dog(dog_id, current_user.id, db)
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    forecast_times = [now + timedelta(hours=offset) for offset in range(0, payload.horizon_hours, payload.interval_hours)]
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
    return rank_walk_windows(dog, intervals, payload.surface)
