from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


@router.get("/", response_model=HealthResponse, summary="Check API availability")
def health_check() -> HealthResponse:
    """Return basic service availability without exposing configuration."""
    return HealthResponse(
        status="ok",
        service="pawguard-api",
        timestamp=datetime.now(UTC),
    )
