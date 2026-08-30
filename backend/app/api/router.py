from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.dogs import router as dogs_router
from app.api.routes.fortyguard import router as fortyguard_router
from app.api.routes.heat_risk import router as heat_risk_router
from app.api.routes.surface_risk import router as surface_risk_router
from app.api.routes.walk_planner import router as walk_planner_router
from app.api.routes.walk_match import router as walk_match_router
from app.api.routes.daily_scheduler import router as daily_scheduler_router
from app.api.routes.route_planner import router as route_planner_router
from app.api.routes.active_walk import router as active_walk_router
from app.api.routes.walks import router as walks_router
from app.api.routes.assistant import router as assistant_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(dogs_router, prefix="/dogs", tags=["dogs"])
api_router.include_router(fortyguard_router, prefix="/fortyguard", tags=["FortyGuard environmental data"])
api_router.include_router(heat_risk_router, prefix="/heat-risk", tags=["dog heat risk"])
api_router.include_router(surface_risk_router, prefix="/surface-risk", tags=["paw surface risk"])
api_router.include_router(walk_planner_router, prefix="/walk-planner", tags=["best walk time"])
api_router.include_router(walk_match_router, prefix="/walk-match", tags=["multi-dog walk match"])
api_router.include_router(daily_scheduler_router, prefix="/walk-scheduler", tags=["daily multi-dog walk scheduler"])
api_router.include_router(route_planner_router, prefix="/route-planner", tags=["heat-aware walk routes"])
api_router.include_router(active_walk_router, prefix="/active-walk", tags=["active walk safety"])
api_router.include_router(walks_router, prefix="/walks", tags=["walk history"])
api_router.include_router(assistant_router, prefix="/assistant", tags=["AI safety assistant"])
