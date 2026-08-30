from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dog(Base):
    __tablename__ = "dogs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    breed: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_size: Mapped[str] = mapped_column(String(20), nullable=False)
    coat_color: Mapped[str | None] = mapped_column(String(80), nullable=True)
    coat_length: Mapped[str] = mapped_column(String(20), nullable=False)
    brachycephalic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(20), nullable=False)
    fitness_level: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="dogs")
    walks: Mapped[list["Walk"]] = relationship(back_populates="dog", passive_deletes=True)
