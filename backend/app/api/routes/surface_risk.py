from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.schemas.surface_risk import SurfaceRiskRequest, SurfaceRiskResponse
from app.services.current_conditions import current_environment
from app.services.surface_risk import calculate_surface_risk

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/dogs/{dog_id}/current", response_model=SurfaceRiskResponse)
def current_surface_risk(dog_id: UUID, payload: SurfaceRiskRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Estimate selected-surface risk using a completed server-side FortyGuard analysis."""
    owned_dog(dog_id, current_user.id, db)
    walk_time = payload.walk_time or datetime.now(UTC).time()
    return calculate_surface_risk(payload.surface, current_environment(payload.latitude, payload.longitude, payload.wait_seconds), walk_time)
