"""Deterministic ranking of forecast heatmap intervals for one dog."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.core.walk_planner_rules import WALK_PLANNER_RULES, WalkPlannerRules
from app.models.dog import Dog
from app.services.heat_risk import calculate_heat_risk
from app.services.surface_risk import calculate_surface_risk


def forecast_temperature_from_result(result: dict[str, Any]) -> float | None:
    """Read the documented heatmap result.stats_data.Temperature_stats mean field."""
    stats = result.get("stats_data") or {}
    temperature_stats = stats.get("Temperature_stats") or stats.get("temperature_stats") or {}
    value = temperature_stats.get("Mean", temperature_stats.get("mean"))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def recommended_walk_duration(dog: Dog, combined_score: int, rules: WalkPlannerRules = WALK_PLANNER_RULES, today: date | None = None) -> int:
    """Return a cautious duration cap shared by individual and multi-dog planning."""
    today = today or date.today()
    minutes = rules.duration_base_minutes + rules.activity_minutes.get(dog.activity_level, 0) + rules.fitness_minutes.get(dog.fitness_level, 0)
    if dog.date_of_birth:
        age = (today - dog.date_of_birth).days / 365.25
        if age < 1 or age >= 7:
            minutes -= 10
    if combined_score >= 75:
        return 0
    if combined_score >= 50:
        return min(minutes, rules.high_risk_cap_minutes)
    if combined_score >= 25:
        return min(minutes, rules.moderate_risk_cap_minutes)
    return max(10, minutes)


def rank_walk_windows(dog: Dog, intervals: list[dict[str, Any]], surface: str | None = None, rules: WalkPlannerRules = WALK_PLANNER_RULES, today: date | None = None) -> dict[str, Any]:
    """Score forecast intervals and rank lowest combined dog/surface estimate first."""
    today = today or date.today()
    windows: list[dict[str, Any]] = []
    for interval in intervals:
        forecast_time: datetime = interval["time"]
        temperature = interval.get("temperature_celsius")
        if temperature is None:
            continue
        environment = {"temperature_celsius": temperature, "apparent_temperature_celsius": temperature, "relative_humidity_percent": None, "solar_ghi_wm2": None}
        heat = calculate_heat_risk(dog, environment, today=today)
        surface_result = calculate_surface_risk(surface, environment, forecast_time.time()) if surface else None
        combined_score = max(heat["score"], surface_result["score"] if surface_result else 0)
        if combined_score < 25:
            level = "Low"
        elif combined_score < 50:
            level = "Moderate"
        elif combined_score < 75:
            level = "High"
        else:
            level = "Very High"
        windows.append({"start": forecast_time.isoformat(), "forecast_temperature_celsius": temperature, "estimated_risk": combined_score, "status": level, "recommended_duration_minutes": recommended_walk_duration(dog, combined_score, rules, today), "heat_risk": heat, "surface_risk": surface_result, "explanation": "Forecast heatmap temperature is used as the environmental estimate. Humidity and solar forecast values are unavailable in this workflow."})
    windows.sort(key=lambda item: (item["estimated_risk"], item["start"]))
    safe = [window for window in windows if window["estimated_risk"] < 50]
    return {"best_window": safe[0] if safe else None, "alternatives": (safe[1:4] if safe else windows[:3]), "all_windows": windows, "message": "No lower-risk forecast window is available in the selected horizon. Consider postponing the walk." if not safe else "Windows are ranked by estimated risk; conditions can change quickly.", "disclaimer": "This is a cautious estimated planning aid, not medical advice or a guarantee of safety. Forecast heatmap temperatures are not a veterinary assessment; monitor your dog and adjust or stop the walk if concerned."}
