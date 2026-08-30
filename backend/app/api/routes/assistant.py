from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.dog import Dog
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.services.current_conditions import current_environment
from app.services.heat_risk import calculate_heat_risk
from app.services.safety_assistant import ask_safety_assistant, base_context, profile_guidance_answer
from app.services.surface_risk import calculate_surface_risk
from app.services.walk_match import match_dogs_for_walk
from app.api.routes.walk_planner import find_best_walk_time
from app.schemas.walk_planner import WalkPlanRequest

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/chat", response_model=AssistantChatResponse)
def chat(payload: AssistantChatRequest, current_user: CurrentUser, db: DbSession) -> dict:
    started_at = perf_counter()
    dogs = list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))
    context = base_context(dogs)
    timings = {"profile_context": round((perf_counter() - started_at) * 1000)}
    used_current_conditions = False
    context_note = "No current location was supplied, so the assistant used dog-profile context only."
    if payload.latitude is not None and payload.longitude is not None:
        context_started_at = perf_counter()
        try:
            environment = current_environment(payload.latitude, payload.longitude, 12)
            selected = next((dog for dog in dogs if str(dog.id) == payload.dog_id), None)
            context["current_environment"] = environment
            context["heat_risk_by_dog"] = [{"dog_name": dog.name, **calculate_heat_risk(dog, environment)} for dog in dogs]
            context["walk_match"] = match_dogs_for_walk(dogs, environment, payload.available_minutes, payload.surface, datetime.now(UTC).time()) if dogs else None
            if selected and payload.surface:
                context["selected_surface_risk"] = calculate_surface_risk(payload.surface, environment, datetime.now(UTC).time())
            if selected and any(term in payload.message.lower() for term in ("when", "safest", "best time", "forecast")):
                try:
                    context["forecast_plan"] = find_best_walk_time(selected.id, WalkPlanRequest(latitude=payload.latitude, longitude=payload.longitude, surface=payload.surface, horizon_hours=12, interval_hours=3, wait_seconds=15), current_user, db)
                except HTTPException as error:
                    context["forecast_plan"] = {"available": False, "message": error.detail}
            used_current_conditions = True
            context_note = "Current FortyGuard conditions and deterministic PawGuard results were included."
        except HTTPException as error:
            context["current_conditions_unavailable"] = error.detail
            context_note = "Current FortyGuard data was temporarily unavailable, so this answer uses saved dog-profile context only; it does not make a live walk recommendation."
        timings["fortyguard_context"] = round((perf_counter() - context_started_at) * 1000)
    elif not dogs:
        context["note"] = "The user has no dog profiles yet."
    ai_started_at = perf_counter()
    answer = ask_safety_assistant(payload.message, context) if used_current_conditions else profile_guidance_answer(payload.message, dogs)
    timings["openai"] = round((perf_counter() - ai_started_at) * 1000) if used_current_conditions else 0
    timings["total"] = round((perf_counter() - started_at) * 1000)
    return {"answer": answer, "used_current_conditions": used_current_conditions, "context_note": context_note, "disclaimer": "PawGuard provides cautious planning guidance, not veterinary diagnosis. Stop activity and seek veterinary help for concerning symptoms.", "timings_ms": timings}
