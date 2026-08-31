"""Opt-in, idempotent sample data seed for PawGuard's dedicated demo account."""
from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.dog import Dog
from app.models.user import User
from app.models.walk import Walk

DEMO_DOGS = (
    ("Max", "Golden Retriever", date(2021, 5, 12), 31.0, "large", "golden", "medium", False, "high", "high", "Enjoys longer walks and shaded park routes."),
    ("Bruno", "French Bulldog", date(2019, 9, 3), 12.5, "small", "brindle", "short", True, "low", "average", "Prefers short, relaxed walks with frequent breaks."),
    ("Luna", "Siberian Husky", date(2020, 2, 18), 23.0, "large", "gray and white", "double", False, "high", "high", "Double coat; enjoys cooler, early-day outings."),
    ("Bella", "Labrador Retriever", date(2022, 7, 9), 27.0, "large", "black", "short", False, "moderate", "high", "Benefits from water breaks on longer walks."),
    ("Coco", "Pomeranian", date(2018, 11, 21), 4.2, "small", "cream", "long", False, "moderate", "average", "Keep walks gentle and monitored."),
)
# Saved samples only: these are not live conditions or provider results.
DEMO_WALKS = (("Bella", 1, 26, "grass", 18, "Low", 12, "Low", 1850), ("Max", 2, 32, "grass", 24, "Low", 18, "Low", 2400), ("Coco", 3, 18, "concrete", 29, "Moderate", 35, "Moderate", 900), ("Bruno", 4, 14, "grass", 34, "Moderate", 20, "Low", 700), ("Luna", 5, 22, "soil_dirt", 20, "Low", 16, "Low", 1650), ("Bella", 7, 30, "grass", 26, "Moderate", 17, "Low", 2100))


def seed_demo_data(db: Session, email: str, password: str | None = None) -> tuple[int, int]:
    """Create missing records for exactly one account; never alter existing ones."""
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        if not password:
            raise ValueError("DEMO_ACCOUNT_PASSWORD is required to create the demo account.")
        user = User(email=email, password_hash=hash_password(password)); db.add(user); db.flush()
    dogs = {dog.name: dog for dog in db.scalars(select(Dog).where(Dog.owner_id == user.id))}
    made_dogs = 0
    for name, breed, dob, weight, size, color, coat, flat, activity, fitness, notes in DEMO_DOGS:
        if name not in dogs:
            dogs[name] = Dog(owner_id=user.id, name=name, breed=breed, date_of_birth=dob, weight_kg=weight, body_size=size, coat_color=color, coat_length=coat, brachycephalic=flat, activity_level=activity, fitness_level=fitness, notes=notes)
            db.add(dogs[name]); made_dogs += 1
    db.flush()
    keys = {meta.get("demo_seed_key") for meta in db.scalars(select(Walk.route_metadata).where(Walk.owner_id == user.id)) if isinstance(meta, dict) and meta.get("source") == "demo_seed"}
    made_walks, now = 0, datetime.now(UTC).replace(second=0, microsecond=0)
    for index, (name, days, minutes, surface, heat, heat_status, paw, paw_status, distance) in enumerate(DEMO_WALKS, 1):
        key = f"walk-{index}"
        if key in keys:
            continue
        db.add(Walk(owner_id=user.id, dog_id=dogs[name].id, dog_name=name, completed_at=now - timedelta(days=days, hours=8), duration_minutes=minutes, surface=surface, heat_risk_score=heat, heat_risk_status=heat_status, surface_risk_score=paw, surface_risk_status=paw_status, route_distance_meters=distance, route_duration_seconds=minutes * 60, route_metadata={"source": "demo_seed", "demo_seed_key": key, "label": "Sample saved walk", "live_conditions": False}))
        made_walks += 1
    db.commit()
    return made_dogs, made_walks


def main() -> None:
    if os.getenv("DEMO_SEED_ENABLED", "").lower() != "true":
        raise SystemExit("Set DEMO_SEED_ENABLED=true to run this one-time command.")
    email = os.getenv("DEMO_ACCOUNT_EMAIL", "").strip()
    if not email:
        raise SystemExit("Set DEMO_ACCOUNT_EMAIL before seeding.")
    with SessionLocal() as db:
        dogs, walks = seed_demo_data(db, email, os.getenv("DEMO_ACCOUNT_PASSWORD"))
    print(f"Demo seed complete: {dogs} dog profile(s), {walks} saved sample walk(s) created.")


if __name__ == "__main__":
    main()
