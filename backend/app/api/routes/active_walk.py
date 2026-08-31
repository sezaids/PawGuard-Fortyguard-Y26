from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.schemas.active_walk import ActiveWalkStatusRequest, ActiveWalkStatusResponse
from app.schemas.fortyguard import CurrentConditionsRequest, DateTimeFilter, HeatmapRequest
from app.services.active_walk import active_walk_summary
from app.services.current_conditions import current_environment
from app.services.fortyguard import FortyGuardError, fortyguard_service
from app.services.heatmap_aoi import heatmap_aoi
from app.services.heat_risk import extract_environment
from app.services.walk_planner import forecast_temperature_from_result

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
_LIVE_DATA_UNAVAILABLE_STATUSES = {202, 429, 502, 503, 504}
_MAX_LIVE_WAIT_SECONDS = 8
_ANALYSIS_TIMEOUT_SECONDS = 120

# Short-lived, server-only bridge from the browser to FortyGuard job IDs. The
# browser only receives PawGuard analysis IDs, and every poll is authorized.
_active_walk_analyses: dict[str, dict] = {}


def unavailable_active_walk_status(reason: str) -> dict:
    """Return a truthful, structured fallback when live provider work is unavailable."""
    return {
        "state": "unavailable",
        "heat_risk": None,
        "surface_risk": None,
        "recommended_duration_minutes": None,
        "reminders": [
            "Do not use a previous estimate as if it were current.",
            "Check conditions again before starting an outdoor walk.",
        ],
        "caution": "PawGuard cannot provide a live walk estimate until FortyGuard conditions are available.",
        "disclaimer": "No environmental or risk values are shown because PawGuard could not verify live FortyGuard conditions. This is not veterinary advice.",
        "unavailable_reason": reason,
    }


def _processing(analysis_id: str, stage: str, message: str) -> dict:
    return {"state": "processing", "analysis_id": analysis_id, "stage": stage, "message": message}


def _unavailable_analysis(analysis_id: str, reason: str) -> dict:
    _active_walk_analyses.pop(analysis_id, None)
    return {**unavailable_active_walk_status(reason), "analysis_id": analysis_id}


def _analysis_for_user(analysis_id: str, current_user: CurrentUser) -> dict:
    analysis = _active_walk_analyses.get(analysis_id)
    if not analysis or analysis["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Active Walk analysis was not found.")
    return analysis


@router.post("/dogs/{dog_id}/analyses")
def start_active_walk_analysis(dog_id: UUID, payload: ActiveWalkStatusRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Create one FortyGuard temperature job and return immediately for polling."""
    owned_dog(dog_id, current_user.id, db)
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    heatmap = HeatmapRequest(
        polygon_aoi=heatmap_aoi(payload.latitude, payload.longitude),
        date_time=DateTimeFilter(start_date=now.date(), start_time=now.strftime("%H:%M"), filter_type=1),
        granularity=100,
        analytic_type="tcm",
    )
    try:
        submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload(), timeout_seconds=8)
    except FortyGuardError as error:
        return unavailable_active_walk_status(str(error.detail))
    provider_id = submitted.get("data", {}).get("activity_id")
    if not provider_id:
        return unavailable_active_walk_status("FortyGuard did not accept the current heat request.")
    analysis_id = str(uuid4())
    _active_walk_analyses[analysis_id] = {
        "owner_id": str(current_user.id),
        "dog_id": dog_id,
        "payload": payload.model_copy(deep=True),
        "provider_id": provider_id,
        "stage": "heatmap",
        "started_at": perf_counter(),
    }
    return _processing(analysis_id, "heatmap", "Analyzing live heat conditions…")


@router.get("/analyses/{analysis_id}")
def poll_active_walk_analysis(analysis_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    """Advance one existing FortyGuard activity per short browser poll."""
    analysis = _analysis_for_user(analysis_id, current_user)
    if perf_counter() - analysis["started_at"] >= _ANALYSIS_TIMEOUT_SECONDS:
        return _unavailable_analysis(analysis_id, "FortyGuard did not complete the live analysis within two minutes. No estimate was produced.")
    if analysis["stage"] == "submitting_environment":
        return _processing(analysis_id, "environment", "Retrieving live environmental details…")

    try:
        provider = fortyguard_service.status(analysis["provider_id"], timeout_seconds=8)
    except FortyGuardError as error:
        return _unavailable_analysis(analysis_id, str(error.detail))
    data = provider.get("data", {})
    provider_status = data.get("status")
    if provider_status == "Failed":
        return _unavailable_analysis(analysis_id, "FortyGuard could not complete the live environmental analysis.")
    if provider_status != "Completed":
        message = "Analyzing live heat conditions…" if analysis["stage"] == "heatmap" else "Retrieving live environmental details…"
        return _processing(analysis_id, analysis["stage"], message)

    payload: ActiveWalkStatusRequest = analysis["payload"]
    if analysis["stage"] == "heatmap":
        temperature = forecast_temperature_from_result(data.get("result") or {})
        if temperature is None:
            return _unavailable_analysis(analysis_id, "FortyGuard returned no usable current temperature for this location.")
        # Mark the transition before submitting to prevent repeated browser
        # polls from creating duplicate environmental jobs.
        analysis["stage"] = "submitting_environment"
        try:
            submitted = fortyguard_service.submit_environment(
                CurrentConditionsRequest(latitude=payload.latitude, longitude=payload.longitude).provider_payload(temperature), timeout_seconds=8
            )
        except FortyGuardError as error:
            return _unavailable_analysis(analysis_id, str(error.detail))
        environment_id = submitted.get("data", {}).get("activity_id")
        if not environment_id:
            return _unavailable_analysis(analysis_id, "FortyGuard did not accept the environmental analysis.")
        analysis.update({"stage": "environment", "provider_id": environment_id, "temperature": temperature})
        return _processing(analysis_id, "environment", "Retrieving live environmental details…")

    environment = extract_environment(data.get("result") or {}, analysis["temperature"])
    if environment.get("temperature_celsius") is None:
        return _unavailable_analysis(analysis_id, "FortyGuard returned incomplete current environmental data.")
    dog = owned_dog(analysis["dog_id"], current_user.id, db)
    result = {"state": "available", **active_walk_summary(dog, environment, payload.surface, payload.walk_time or datetime.now(UTC).time())}
    _active_walk_analyses.pop(analysis_id, None)
    return {"state": "completed", "analysis_id": analysis_id, "result": result}


@router.post("/dogs/{dog_id}/status", response_model=ActiveWalkStatusResponse)
def current_active_walk_status(dog_id: UUID, payload: ActiveWalkStatusRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Compatibility endpoint for callers that still require one short live check."""
    dog = owned_dog(dog_id, current_user.id, db)
    try:
        environment = current_environment(payload.latitude, payload.longitude, min(payload.wait_seconds, _MAX_LIVE_WAIT_SECONDS))
    except HTTPException as error:
        if error.status_code in _LIVE_DATA_UNAVAILABLE_STATUSES:
            return unavailable_active_walk_status(str(error.detail))
        raise
    return active_walk_summary(dog, environment, payload.surface, payload.walk_time or datetime.now(UTC).time())
