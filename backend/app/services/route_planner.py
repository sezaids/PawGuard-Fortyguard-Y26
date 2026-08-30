"""Compose OSRM walking geometries with completed FortyGuard heatmap tiles."""
from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from time import perf_counter
from typing import Any

from fastapi import HTTPException

from app.core.route_rules import ROUTE_RULES, RouteRules
from app.schemas.fortyguard import HeatmapRequest
from app.services.fortyguard import fortyguard_service
from app.services.heatmap_view import heatmap_view_from_activity
from app.services.route_heat import add_relative_heat_exposure, rank_routes
from app.services.routing import routing_service

_pending_route_jobs: dict[str, dict[str, Any]] = {}
ROUTE_HEAT_ANALYSIS_TIMEOUT_SECONDS = 120


def _route_option(index: int, route: dict[str, Any]) -> dict[str, Any]:
    geometry = route.get("geometry") or {}
    return {"id": f"route-{index + 1}", "geometry": geometry, "distance_meters": float(route["distance"]), "duration_seconds": float(route["duration"]), "estimated_walking_minutes": max(1, ceil(float(route["duration"]) / 60)), "relative_heat_exposure": None, "heat_optimized": False, "explanation": "Real walking route geometry returned by the routing provider."}


def _route_aoi(routes: list[dict[str, Any]]) -> dict[str, Any]:
    coordinates = [point for route in routes for point in route["geometry"].get("coordinates") or []]
    longitudes = [point[0] for point in coordinates]; latitudes = [point[1] for point in coordinates]
    delta = 0.0015
    min_lon, max_lon = min(longitudes) - delta, max(longitudes) + delta
    min_lat, max_lat = min(latitudes) - delta, max(latitudes) + delta
    ring = [[min_lon, min_lat], [max_lon, min_lat], [max_lon, max_lat], [min_lon, max_lat], [min_lon, min_lat]]
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def _loop_routes(start: tuple[float, float], rules: RouteRules) -> list[dict[str, Any]]:
    latitude, longitude = start; delta = rules.loop_waypoint_offset_degrees
    waypoint_sets = [
        [(latitude, longitude), (latitude + delta, longitude + delta), (latitude - delta, longitude + delta), (latitude - delta, longitude - delta), (latitude, longitude)],
        [(latitude, longitude), (latitude + delta, longitude - delta), (latitude + delta, longitude + delta), (latitude - delta, longitude + delta), (latitude, longitude)],
    ]
    routes: list[dict[str, Any]] = []
    for waypoints in waypoint_sets:
        routes.extend(routing_service.routes(waypoints))
    return routes


def _response(routes: list[dict[str, Any]], heat_available: bool, heatmap: dict[str, Any] | None, message: str, rules: RouteRules, activity_id: str | None = None) -> dict[str, Any]:
    ranked = rank_routes(routes, heat_available, rules)
    for route in ranked:
        exposure = route.get("relative_heat_exposure")
        route["explanation"] = f"Selected using walking time plus a transparent relative heat-exposure index of {exposure}/100 from available FortyGuard tiles; detour stays within {round((rules.max_detour_ratio - 1) * 100)}% of the shortest route." if route["heat_optimized"] and exposure is not None else ("This real walking route is ranked by normal walking time while heat analysis is unavailable." if not heat_available else "This real walking alternative exceeds the configured reasonable-detour limit.")
        route.pop("_cost", None)
    return {"recommended_route": ranked[0], "alternatives": ranked[1:], "heat_optimization_available": heat_available, "message": message, "heatmap": heatmap, "heat_activity_id": activity_id, "disclaimer": "Relative heat exposure is estimated only from completed FortyGuard heatmap tiles along the route geometry. It is not a street-level temperature measurement or a guarantee of safety; check conditions and your dog throughout the walk."}


def poll_heat_aware_route(activity_id: str, rules: RouteRules = ROUTE_RULES) -> dict[str, Any]:
    pending = _pending_route_jobs.get(activity_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Route heat analysis was not found.")
    routes = pending["routes"]
    if perf_counter() - pending["started_at"] >= ROUTE_HEAT_ANALYSIS_TIMEOUT_SECONDS:
        _pending_route_jobs.pop(activity_id, None)
        return _response(routes, False, None, "FortyGuard did not complete route heat analysis within two minutes; routes are ranked by normal walking time.", rules)
    activity = fortyguard_service.status(activity_id)
    view = heatmap_view_from_activity(activity)
    if view["state"] == "processing":
        return _response(routes, False, None, "Analyzing route heat exposure… Routes are currently ranked by normal walking time.", rules, activity_id)
    _pending_route_jobs.pop(activity_id, None)
    if view["state"] == "completed" and view["map_data"]:
        exposed = add_relative_heat_exposure(routes, view["map_data"], rules)
        available = any(route.get("relative_heat_exposure") is not None for route in exposed)
        return _response(exposed, available, view["map_data"], "Route heat exposure is estimated from completed FortyGuard tiles, not street-level temperature measurements." if available else "FortyGuard returned no usable route heat values; routes are ranked by normal walking time.", rules)
    return _response(routes, False, None, "Heat optimization is unavailable; routes are ranked by normal walking time.", rules)


def plan_heat_aware_routes(start: tuple[float, float], destination: tuple[float, float] | None, mode: str, heat_wait_seconds: int, rules: RouteRules = ROUTE_RULES) -> dict[str, Any]:
    raw_routes = _loop_routes(start, rules) if mode == "loop" else routing_service.routes([start, destination], alternatives=True)
    routes = [_route_option(index, route) for index, route in enumerate(raw_routes) if route.get("geometry", {}).get("type") == "LineString"]
    if not routes:
        raise HTTPException(status_code=422, detail="The walking routing provider returned no usable route geometry.")

    heat_available = False; heatmap = None; heat_message = "Heat optimization is unavailable; routes are ranked by normal walking time."
    try:
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        heatmap_request = HeatmapRequest(polygon_aoi=_route_aoi(routes), date_time={"start_date": now.date(), "start_time": now.strftime("%H:%M"), "filter_type": 1}, granularity=100, analytic_type="tcm")
        submitted = fortyguard_service.submit_heatmap(heatmap_request.provider_payload())
        activity_id = submitted.get("data", {}).get("activity_id")
        if activity_id:
            _pending_route_jobs[activity_id] = {"routes": routes, "started_at": perf_counter()}
            return _response(routes, False, None, "Analyzing route heat exposure… Routes are currently ranked by normal walking time.", rules, activity_id)
    except HTTPException as error:
        # A routing result is still useful when provider heat coverage, quota, or
        # processing is unavailable. Never substitute made-up heat values.
        heat_message = f"Heat optimization is unavailable: {error.detail} Routes are ranked by normal walking time."

    return _response(routes, heat_available, heatmap, heat_message, rules)
