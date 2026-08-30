from datetime import UTC, datetime
import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.schemas.fortyguard import ActivityResponse, CurrentConditionsRequest, HeatmapRequest
from app.schemas.heatmap_view import HeatmapViewRequest, HeatmapViewResponse
from app.services.current_conditions import current_environment
from app.services.fortyguard import fortyguard_service
from app.services.heatmap_aoi import heatmap_aoi
from app.services.heatmap_view import heatmap_view_from_activity

router = APIRouter()
logger = logging.getLogger(__name__)
HEATMAP_PROCESSING_TIMEOUT_SECONDS = 120
_heatmap_activities: dict[str, dict[str, object]] = {}

AVAILABLE_PARAMETERS = [
    "heat_index_celsius", "apparent_temperature_celsius", "relative_humidity_percent", "precipitation_mm",
    "cloud_cover_metric", "wet_bulb_temperature_celsius", "aqi_us", "aqi_us_pm25", "aqi_us_pm10",
    "aqi_us_no2", "aqi_us_co", "aqi_us_o3", "aqi_us_so2", "methane_ppb", "co2_ppm",
    "solar_irradiance.clear_sky.ghi", "solar_irradiance.clear_sky.dni", "solar_irradiance.clear_sky.dhi",
]


@router.get("/parameters")
def available_parameters(current_user: CurrentUser) -> dict[str, list[str]]:
    """Document the official environmental fields that a completed job may return."""
    return {"parameters": AVAILABLE_PARAMETERS}


@router.post("/current")
def current_conditions(payload: CurrentConditionsRequest, current_user: CurrentUser) -> dict:
    """Return a current server-derived environmental snapshot for a location."""
    return {"environment": current_environment(payload.latitude, payload.longitude, payload.wait_seconds)}


@router.post("/forecast", response_model=ActivityResponse)
def forecast_heatmap(payload: HeatmapRequest, current_user: CurrentUser) -> dict:
    """Submit FortyGuard's documented heatmap workflow, including up to 12-hour forecasts."""
    submitted = fortyguard_service.submit_heatmap(payload.provider_payload())
    activity_id = submitted.get("data", {}).get("activity_id")
    return fortyguard_service.wait_for_completion(activity_id, payload.wait_seconds) if activity_id and payload.wait_seconds else submitted


@router.post("/heatmaps", response_model=ActivityResponse)
def create_heatmap(payload: HeatmapRequest, current_user: CurrentUser) -> dict:
    return forecast_heatmap(payload, current_user)


@router.get("/activities/{activity_id}", response_model=ActivityResponse)
def activity_status(activity_id: str, current_user: CurrentUser) -> dict:
    return fortyguard_service.status(activity_id)


@router.post("/heatmap-view", response_model=HeatmapViewResponse)
def create_heatmap_view(payload: HeatmapViewRequest, current_user: CurrentUser) -> dict:
    """Submit a real FortyGuard GeoJSON job; the browser polls the protected status route."""
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    heatmap = HeatmapRequest(polygon_aoi=heatmap_aoi(payload.latitude, payload.longitude), date_time={"start_date": now.date(), "start_time": now.strftime("%H:%M"), "filter_type": 1}, granularity=100, analytic_type="tcm")
    submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload())
    activity_id = submitted.get("data", {}).get("activity_id")
    view = heatmap_view_from_activity(submitted)
    if activity_id:
        _heatmap_activities[activity_id] = {"owner_id": str(current_user.id), "started_at": perf_counter(), "last_state": view["state"], "polls": 0}
        logger.info("Heat Map activity submitted: activity=%s state=%s", activity_id, view["state"])
    return view


@router.get("/heatmap-view/activities/{activity_id}", response_model=HeatmapViewResponse)
def heatmap_view_status(activity_id: str, current_user: CurrentUser) -> dict:
    """Poll a heatmap activity and expose only its documented view fields."""
    tracked = _heatmap_activities.get(activity_id)
    if not tracked or tracked["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Heat Map activity was not found.")
    if perf_counter() - float(tracked["started_at"]) >= HEATMAP_PROCESSING_TIMEOUT_SECONDS:
        _heatmap_activities.pop(activity_id, None)
        logger.warning("Heat Map activity timed out: activity=%s", activity_id)
        return {"state": "failed", "activity_id": activity_id, "message": "FortyGuard did not complete this heatmap within two minutes. No map values were used.", "map_data": None, "stats_data": None}
    view = heatmap_view_from_activity(fortyguard_service.status(activity_id))
    tracked["polls"] = int(tracked["polls"]) + 1
    if tracked["last_state"] != view["state"]:
        logger.info("Heat Map activity transition: activity=%s %s→%s", activity_id, tracked["last_state"], view["state"])
        tracked["last_state"] = view["state"]
    if view["state"] != "processing":
        _heatmap_activities.pop(activity_id, None)
    return view
