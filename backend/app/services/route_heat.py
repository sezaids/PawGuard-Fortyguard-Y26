"""Associate real route geometry with real completed FortyGuard tile values."""
from __future__ import annotations

from typing import Any

from app.core.route_rules import ROUTE_RULES, RouteRules


def provider_tile_value(properties: dict[str, Any] | None) -> float | None:
    """Use only a numeric provider property explicitly named as a tile measurement."""
    for key, value in (properties or {}).items():
        if any(token in key.lower() for token in ("temperature", "tcm", "value")):
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def _inside(point: list[float], ring: list[list[float]]) -> bool:
    x, y = point; inside = False
    for index, current in enumerate(ring):
        previous = ring[index - 1]
        x1, y1 = previous; x2, y2 = current
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _tile_samples(map_data: dict[str, Any], coordinate: list[float]) -> list[float]:
    values: list[float] = []
    for feature in map_data.get("features") or []:
        value = provider_tile_value(feature.get("properties"))
        geometry = feature.get("geometry") or {}; coordinates = geometry.get("coordinates") or []
        polygons = coordinates if geometry.get("type") == "MultiPolygon" else [coordinates] if geometry.get("type") == "Polygon" else []
        if value is not None and any(_inside(coordinate, ring) for polygon in polygons for ring in polygon[:1]):
            values.append(value)
    return values


def add_relative_heat_exposure(routes: list[dict[str, Any]], map_data: dict[str, Any], rules: RouteRules = ROUTE_RULES) -> list[dict[str, Any]]:
    """Return a 0–100 relative index, not a street-level temperature claim."""
    all_values = [provider_tile_value(feature.get("properties")) for feature in map_data.get("features") or []]
    all_values = [value for value in all_values if value is not None]
    if not all_values:
        return [{**route, "relative_heat_exposure": None} for route in routes]
    low, high = min(all_values), max(all_values)
    enriched = []
    for route in routes:
        samples = [value for coordinate in route["geometry"].get("coordinates") or [] for value in _tile_samples(map_data, coordinate)]
        if not samples:
            enriched.append({**route, "relative_heat_exposure": None})
            continue
        mean = sum(samples) / len(samples)
        relative = 50 if high == low else round((mean - low) / (high - low) * 100)
        enriched.append({**route, "relative_heat_exposure": max(0, min(100, relative))})
    return enriched


def rank_routes(routes: list[dict[str, Any]], heat_available: bool, rules: RouteRules = ROUTE_RULES) -> list[dict[str, Any]]:
    """Prefer cooler routes only inside the configured reasonable-detour bound."""
    shortest = min(route["distance_meters"] for route in routes)
    for route in routes:
        reasonable = route["distance_meters"] <= shortest * rules.max_detour_ratio
        exposure = route.get("relative_heat_exposure")
        route["heat_optimized"] = bool(heat_available and reasonable and exposure is not None)
        route["_cost"] = route["duration_seconds"] + (rules.heat_weight_seconds * exposure / 100 if route["heat_optimized"] else 0)
    return sorted(routes, key=lambda route: (route["_cost"] if route["heat_optimized"] else route["duration_seconds"], route["distance_meters"]))
