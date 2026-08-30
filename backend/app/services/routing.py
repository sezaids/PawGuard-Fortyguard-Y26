"""Server-side OSRM walking route client. No browser provider credentials are used."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


class RoutingError(HTTPException):
    pass


class RoutingService:
    def routes(self, coordinates: list[tuple[float, float]], alternatives: bool = False) -> list[dict[str, Any]]:
        settings = get_settings()
        encoded = ";".join(f"{longitude:.7f},{latitude:.7f}" for latitude, longitude in coordinates)
        url = f"{settings.routing_base_url.rstrip('/')}/route/v1/{settings.routing_profile}/{encoded}"
        try:
            with httpx.Client(timeout=httpx.Timeout(settings.routing_timeout_seconds)) as client:
                response = client.get(url, params={"alternatives": str(alternatives).lower(), "steps": "false", "geometries": "geojson", "overview": "full"})
        except httpx.TimeoutException as error:
            raise RoutingError(status_code=504, detail="The walking routing provider timed out. Please try again.") from error
        except httpx.RequestError as error:
            raise RoutingError(status_code=502, detail="PawGuard could not reach the walking routing provider.") from error
        if response.status_code >= 400:
            raise RoutingError(status_code=502, detail="The walking routing provider could not create a route for those locations.")
        try:
            payload = response.json()
        except ValueError as error:
            raise RoutingError(status_code=502, detail="The walking routing provider returned an unreadable response.") from error
        routes = payload.get("routes") if payload.get("code") == "Ok" else None
        if not isinstance(routes, list) or not routes:
            raise RoutingError(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No walkable route is available between those locations.")
        return routes


routing_service = RoutingService()
