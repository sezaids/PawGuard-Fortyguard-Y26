from datetime import UTC, datetime
from uuid import uuid4
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.dog import Dog
from app.schemas.walk_match import WalkMatchRequest, WalkMatchResponse
from app.schemas.fortyguard import CurrentConditionsRequest, DateTimeFilter, HeatmapRequest
from app.services.fortyguard import fortyguard_service
from app.services.current_conditions import current_environment
from app.services.heatmap_aoi import heatmap_aoi
from app.services.heat_risk import extract_environment
from app.services.walk_planner import forecast_temperature_from_result
from app.services.walk_match import match_dogs_for_walk

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
_analyses: dict[str, dict] = {}


@router.post("/analyses")
def start_walk_match_analysis(payload: WalkMatchRequest, current_user: CurrentUser, db: DbSession) -> dict:
    dogs = list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))
    if not dogs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Add a dog profile before using Walk Match.")
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    heatmap = HeatmapRequest(polygon_aoi=heatmap_aoi(payload.latitude, payload.longitude), date_time=DateTimeFilter(start_date=now.date(), start_time=now.strftime("%H:%M"), filter_type=1), granularity=100, analytic_type="tcm")
    submitted = fortyguard_service.submit_heatmap(heatmap.provider_payload())
    provider_id = submitted.get("data", {}).get("activity_id")
    if not provider_id:
        raise HTTPException(status_code=502, detail="FortyGuard did not accept the live heat analysis.")
    analysis_id = str(uuid4())
    _analyses[analysis_id] = {"owner_id": str(current_user.id), "payload": payload, "stage": "heatmap", "provider_id": provider_id}
    return {"state": "processing", "analysis_id": analysis_id, "stage": "heatmap", "message": "Analyzing live heat conditions…"}


@router.get("/analyses/{analysis_id}")
def poll_walk_match_analysis(analysis_id: str, current_user: CurrentUser, db: DbSession) -> dict:
    analysis = _analyses.get(analysis_id)
    if not analysis or analysis["owner_id"] != str(current_user.id):
        raise HTTPException(status_code=404, detail="Walk Match analysis was not found.")
    provider = fortyguard_service.status(analysis["provider_id"])
    data = provider.get("data", {})
    if data.get("status") == "Failed":
        _analyses.pop(analysis_id, None)
        raise HTTPException(status_code=502, detail="FortyGuard could not complete the live heat analysis.")
    if data.get("status") != "Completed":
        return {"state": "processing", "analysis_id": analysis_id, "stage": analysis["stage"], "message": "Analyzing live heat conditions…" if analysis["stage"] == "heatmap" else "Retrieving live environmental details…"}
    payload: WalkMatchRequest = analysis["payload"]
    if analysis["stage"] == "heatmap":
        temperature = forecast_temperature_from_result(data.get("result") or {})
        if temperature is None:
            _analyses.pop(analysis_id, None)
            raise HTTPException(status_code=502, detail="FortyGuard returned no usable current temperature.")
        submitted = fortyguard_service.submit_environment(CurrentConditionsRequest(latitude=payload.latitude, longitude=payload.longitude).provider_payload(temperature))
        provider_id = submitted.get("data", {}).get("activity_id")
        if not provider_id:
            _analyses.pop(analysis_id, None)
            raise HTTPException(status_code=502, detail="FortyGuard did not accept the environmental analysis.")
        analysis.update({"stage": "environment", "provider_id": provider_id, "temperature": temperature})
        return {"state": "processing", "analysis_id": analysis_id, "stage": "environment", "message": "Retrieving live environmental details…"}
    environment = extract_environment(data.get("result") or {}, analysis["temperature"])
    dogs = list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))
    result = match_dogs_for_walk(dogs, environment, payload.available_minutes, payload.surface, payload.walk_time or datetime.now(UTC).time())
    _analyses.pop(analysis_id, None)
    return {"state": "completed", "result": result}


@router.post("/current", response_model=WalkMatchResponse)
def walk_match_now(payload: WalkMatchRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Evaluate every dog owned by the current user from one current environmental analysis."""
    dogs = list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))
    if not dogs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Add a dog profile before using Walk Match.")
    environment = current_environment(payload.latitude, payload.longitude, payload.wait_seconds)
    return match_dogs_for_walk(dogs, environment, payload.available_minutes, payload.surface, payload.walk_time or datetime.now(UTC).time())
