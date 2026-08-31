from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.schemas.active_walk import ActiveWalkStatusRequest, ActiveWalkStatusResponse
from app.services.active_walk import active_walk_summary
from app.services.current_conditions import current_environment

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
_LIVE_DATA_UNAVAILABLE_STATUSES = {202, 429, 502, 503, 504}
# Active Walk needs two provider activities. Bound the synchronous attempt so a
# slow provider results in the structured unavailable state before an upstream
# proxy can terminate the browser request.
_MAX_LIVE_WAIT_SECONDS = 8


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


@router.post("/dogs/{dog_id}/status", response_model=ActiveWalkStatusResponse)
def current_active_walk_status(dog_id: UUID, payload: ActiveWalkStatusRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Use one completed server-side environmental analysis for Active Walk status."""
    dog = owned_dog(dog_id, current_user.id, db)
    try:
        environment = current_environment(payload.latitude, payload.longitude, min(payload.wait_seconds, _MAX_LIVE_WAIT_SECONDS))
    except HTTPException as error:
        if error.status_code in _LIVE_DATA_UNAVAILABLE_STATUSES:
            return unavailable_active_walk_status(str(error.detail))
        raise
    return active_walk_summary(dog, environment, payload.surface, payload.walk_time or datetime.now(UTC).time())
