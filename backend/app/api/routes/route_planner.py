from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.route_planner import RoutePlanRequest, RoutePlanResponse
from app.services.route_planner import plan_heat_aware_routes, poll_heat_aware_route

router = APIRouter()


@router.post("/plan", response_model=RoutePlanResponse)
def plan_route(payload: RoutePlanRequest, current_user: CurrentUser) -> dict:
    """Create real walking routes and improve their ranking only with completed heat tiles."""
    start = (payload.start.latitude, payload.start.longitude)
    destination = (payload.destination.latitude, payload.destination.longitude) if payload.destination else None
    return plan_heat_aware_routes(start, destination, payload.mode, payload.heat_wait_seconds)


@router.get("/activities/{activity_id}", response_model=RoutePlanResponse)
def poll_route_heat(activity_id: str, current_user: CurrentUser) -> dict:
    return poll_heat_aware_route(activity_id)
