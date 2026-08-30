from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    dogs: Mapped[list["Dog"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    walks: Mapped[list["Walk"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
