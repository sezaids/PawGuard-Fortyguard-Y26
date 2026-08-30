"""Build a current environmental snapshot from real FortyGuard results only."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status

from app.schemas.fortyguard import CurrentConditionsRequest, DateTimeFilter, HeatmapRequest
from app.services.fortyguard import fortyguard_service
from app.services.heatmap_aoi import heatmap_aoi
from app.services.heat_risk import extract_environment
from app.services.walk_planner import forecast_temperature_from_result


def _completed_or_error(activity: dict, unavailable_message: str) -> dict:
    data = activity.get("data", {})
    if data.get("status") == "Failed":
        raise HTTPException(status_code=502, detail=unavailable_message)
    if data.get("status") != "Completed":
        raise HTTPException(status_code=status.HTTP_202_ACCEPTED, detail="FortyGuard is still processing this location. Please retry shortly.")
    return data.get("result") or {}


def current_environment(latitude: float, longitude: float, wait_seconds: int) -> dict[str, float | None]:
    """Use a current FortyGuard temperature tile as the required env_params input.

    This avoids asking users for a temperature and never substitutes a made-up value.
    """
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    heatmap = HeatmapRequest(
        polygon_aoi=heatmap_aoi(latitude, longitude),
        date_time=DateTimeFilter(start_date=now.date(), start_time=now.strftime("%H:%M"), filter_type=1),
        granularity=100,
        analytic_type="tcm",
    )
    submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload())
    activity_id = submitted.get("data", {}).get("activity_id")
    if not activity_id:
        raise HTTPException(status_code=502, detail="FortyGuard did not accept the current heat request.")
    heatmap_result = _completed_or_error(fortyguard_service.wait_for_completion(activity_id, wait_seconds), "FortyGuard could not complete the current temperature map.")
    temperature = forecast_temperature_from_result(heatmap_result)
    if temperature is None:
        raise HTTPException(status_code=502, detail="FortyGuard returned no usable current temperature for this location.")

    environmental = CurrentConditionsRequest(latitude=latitude, longitude=longitude).provider_payload(temperature)
    submitted = fortyguard_service.submit_environment(environmental)
    activity_id = submitted.get("data", {}).get("activity_id")
    if not activity_id:
        raise HTTPException(status_code=502, detail="FortyGuard did not accept the environmental request.")
    result = _completed_or_error(fortyguard_service.wait_for_completion(activity_id, wait_seconds), "FortyGuard could not complete the current environmental analysis.")
    environment = extract_environment(result, temperature)
    if environment.get("temperature_celsius") is None:
        raise HTTPException(status_code=502, detail="FortyGuard returned incomplete current environmental data.")
    return environment
