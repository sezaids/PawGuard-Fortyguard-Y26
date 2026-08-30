"""Pure surface-risk estimate based on documented environmental inputs."""
from __future__ import annotations

from datetime import time
from typing import Any

from app.core.surface_risk_rules import SURFACE_RISK_RULES, SurfaceRiskRules

_SURFACE_LABELS = {"asphalt": "Asphalt", "concrete": "Concrete", "grass": "Grass", "sand": "Sand", "soil_dirt": "Soil / dirt"}


def calculate_surface_risk(surface: str, environment: dict[str, float | None], walk_time: time, rules: SurfaceRiskRules = SURFACE_RISK_RULES) -> dict[str, Any]:
    """Return an explainable relative risk, never a claimed surface temperature."""
    factors: list[dict[str, Any]] = []

    def add(factor: str, points: int, detail: str) -> None:
        if points:
            factors.append({"factor": factor, "points": points, "detail": detail})

    apparent = environment.get("apparent_temperature_celsius") or environment.get("temperature_celsius") or 0
    for upper_limit, points in rules.temperature_bands:
        if apparent <= upper_limit:
            add("Current heat conditions", points, f"apparent temperature {apparent:.1f}°C")
            break
    add("Selected surface", rules.surface_points[surface], _SURFACE_LABELS[surface])
    solar = environment.get("solar_ghi_wm2")
    if solar is not None:
        solar_points = 14 if solar >= rules.solar_high_wm2 else 7 if solar >= rules.solar_moderate_wm2 else 0
        add("Solar exposure", solar_points, f"{solar:.0f} W/m² clear-sky GHI")
    if rules.midday_start_hour <= walk_time.hour < rules.midday_end_hour:
        add("Time of day", 6, f"{walk_time.strftime('%H:%M')} falls in the higher-sun window")

    score = min(100, sum(item["points"] for item in factors))
    if score < 25:
        level, reason, alternatives = "Low", f"{_SURFACE_LABELS[surface]} is estimated to have relatively low heat exposure under these conditions.", ["Continue to check the surface with the back of your hand.", "Prefer shaded routes when available."]
    elif score < 50:
        level, reason, alternatives = "Moderate", f"{_SURFACE_LABELS[surface]} may retain or absorb enough heat to be uncomfortable, especially in sun.", ["Prefer grass or shaded soil/dirt where practical.", "Keep the walk short and check the surface often."]
    elif score < 75:
        level, reason, alternatives = "High", f"Sun and current heat conditions can make {surface.replace('_', ' ')} uncomfortable or hazardous for paws.", ["Choose shaded grass or postpone the walk.", "Avoid long stretches of asphalt, concrete, and sand."]
    else:
        level, reason, alternatives = "Very High", f"{_SURFACE_LABELS[surface]} is estimated to present substantial heat exposure in these conditions.", ["Avoid this surface now; postpone outdoor walking if possible.", "Use a cooler shaded grass route only if essential and monitor your dog closely."]
    return {"score": score, "level": level, "surface": surface, "reason": reason, "main_factors": sorted(factors, key=lambda item: item["points"], reverse=True)[:4], "safer_alternatives": alternatives, "environment": environment, "disclaimer": "This is a relative paw-surface risk estimate, not an exact pavement-temperature measurement. FortyGuard does not provide an exact surface temperature. Check the surface yourself and stop if it feels too hot for your hand."}
