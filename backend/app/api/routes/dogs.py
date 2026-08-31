from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.models.dog import Dog
from app.schemas.dog import DogCreate, DogResponse, DogUpdate

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


def owned_dog(dog_id: UUID, owner_id: UUID, db: Session) -> Dog:
    dog = db.scalar(select(Dog).where(Dog.id == dog_id, Dog.owner_id == owner_id))
    if not dog:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dog profile not found")
    return dog


@router.get("", response_model=list[DogResponse])
def list_dogs(current_user: CurrentUser, db: DbSession) -> list[Dog]:
    return list(db.scalars(select(Dog).where(Dog.owner_id == current_user.id).order_by(Dog.name)))


@router.post("", response_model=DogResponse, status_code=status.HTTP_201_CREATED)
def create_dog(payload: DogCreate, current_user: CurrentUser, db: DbSession) -> Dog:
    dog = Dog(owner_id=current_user.id, **payload.model_dump())
    db.add(dog)
    db.commit()
    db.refresh(dog)
    return dog


@router.get("/{dog_id}", response_model=DogResponse)
def get_dog(dog_id: UUID, current_user: CurrentUser, db: DbSession) -> Dog:
    return owned_dog(dog_id, current_user.id, db)


@router.put("/{dog_id}", response_model=DogResponse)
def update_dog(dog_id: UUID, payload: DogUpdate, current_user: CurrentUser, db: DbSession) -> Dog:
    dog = owned_dog(dog_id, current_user.id, db)
    for field, value in payload.model_dump().items():
        setattr(dog, field, value)
    db.commit()
    db.refresh(dog)
    return dog


@router.delete("/{dog_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dog(dog_id: UUID, current_user: CurrentUser, db: DbSession) -> Response:
    dog = owned_dog(dog_id, current_user.id, db)
    db.delete(dog)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
