"""Configurable, transparent safety constraints for heat-aware route ranking."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRules:
    max_detour_ratio: float = 1.20
    heat_weight_seconds: int = 600
    loop_waypoint_offset_degrees: float = 0.0035


ROUTE_RULES = RouteRules()
