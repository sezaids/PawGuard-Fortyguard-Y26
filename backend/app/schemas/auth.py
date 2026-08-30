from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(UserCreate):
    pass


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr

    model_config = {"from_attributes": True}
