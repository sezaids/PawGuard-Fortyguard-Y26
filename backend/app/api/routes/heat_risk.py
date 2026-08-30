from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.schemas.heat_risk import CurrentRiskRequest, HeatRiskResponse
from app.services.current_conditions import current_environment
from app.services.heat_risk import calculate_heat_risk

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/dogs/{dog_id}/current", response_model=HeatRiskResponse)
def current_dog_heat_risk(dog_id: UUID, payload: CurrentRiskRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Use a completed FortyGuard environmental job to estimate one dog's current heat risk."""
    dog = owned_dog(dog_id, current_user.id, db)
    return calculate_heat_risk(dog, current_environment(payload.latitude, payload.longitude, payload.wait_seconds))
