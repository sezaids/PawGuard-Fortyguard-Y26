from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.schemas.active_walk import ActiveWalkStatusRequest, ActiveWalkStatusResponse
from app.services.active_walk import active_walk_summary
from app.services.current_conditions import current_environment

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/dogs/{dog_id}/status", response_model=ActiveWalkStatusResponse)
def current_active_walk_status(dog_id: UUID, payload: ActiveWalkStatusRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """Use one completed server-side environmental analysis for Active Walk status."""
    dog = owned_dog(dog_id, current_user.id, db)
    environment = current_environment(payload.latitude, payload.longitude, payload.wait_seconds)
    return active_walk_summary(dog, environment, payload.surface, payload.walk_time or datetime.now(UTC).time())
