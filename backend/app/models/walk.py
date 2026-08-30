from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Walk(Base):
    __tablename__ = "walks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    dog_id: Mapped[UUID | None] = mapped_column(ForeignKey("dogs.id", ondelete="SET NULL"), index=True, nullable=True)
    dog_name: Mapped[str] = mapped_column(String(100), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    surface: Mapped[str] = mapped_column(String(20), nullable=False)
    heat_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heat_risk_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    surface_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surface_risk_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    route_distance_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    route_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    owner: Mapped["User"] = relationship(back_populates="walks")
    dog: Mapped["Dog | None"] = relationship(back_populates="walks")
