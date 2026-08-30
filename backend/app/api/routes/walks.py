from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.api.routes.dogs import owned_dog
from app.db.session import get_db
from app.models.walk import Walk
from app.schemas.walk import WalkCreate, WalkHistorySummary, WalkResponse
from app.services.walk_history import build_walk_summary

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/", response_model=WalkResponse, status_code=status.HTTP_201_CREATED)
def save_walk(payload: WalkCreate, current_user: CurrentUser, db: DbSession) -> Walk:
    dog = owned_dog(payload.dog_id, current_user.id, db)
    walk = Walk(owner_id=current_user.id, dog_id=dog.id, dog_name=dog.name, completed_at=payload.completed_at or datetime.now(UTC), **payload.model_dump(exclude={"dog_id", "completed_at"}))
    db.add(walk); db.commit(); db.refresh(walk)
    return walk


@router.get("/", response_model=list[WalkResponse])
def list_walks(current_user: CurrentUser, db: DbSession) -> list[Walk]:
    return list(db.scalars(select(Walk).where(Walk.owner_id == current_user.id).order_by(Walk.completed_at.desc()).limit(100)))


@router.get("/summary", response_model=WalkHistorySummary)
def walk_summary(current_user: CurrentUser, db: DbSession) -> dict:
    walks = list(db.scalars(select(Walk).where(Walk.owner_id == current_user.id).order_by(Walk.completed_at.desc()).limit(100)))
    return build_walk_summary(walks)
