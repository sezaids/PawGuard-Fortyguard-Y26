from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DogBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    breed: str = Field(min_length=1, max_length=120)
    date_of_birth: date | None = None
    weight_kg: float | None = Field(default=None, gt=0, le=250)
    body_size: str = Field(pattern="^(small|medium|large|giant)$")
    coat_color: str | None = Field(default=None, max_length=80)
    coat_length: str = Field(pattern="^(short|medium|long|double)$")
    brachycephalic: bool = False
    activity_level: str = Field(pattern="^(low|moderate|high)$")
    fitness_level: str = Field(pattern="^(low|average|high)$")
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "breed", "coat_color", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class DogCreate(DogBase):
    pass


class DogUpdate(DogBase):
    pass


class DogResponse(DogBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
