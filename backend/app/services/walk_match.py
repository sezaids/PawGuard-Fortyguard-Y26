"""Deterministic 'which dog can I walk now?' ranking using shared conditions."""
from __future__ import annotations

from datetime import date, time
from typing import Any

from app.models.dog import Dog
from app.services.heat_risk import calculate_heat_risk
from app.services.surface_risk import calculate_surface_risk
from app.services.walk_planner import recommended_walk_duration


def _level(score: int) -> str:
    if score < 25:
        return "Low"
    if score < 50:
        return "Moderate"
    if score < 75:
        return "High"
    return "Very High"


def match_dogs_for_walk(dogs: list[Dog], environment: dict[str, float | None], available_minutes: int, surface: str | None = None, walk_time: time | None = None, today: date | None = None) -> dict[str, Any]:
    """Rank all supplied dogs by complete existing risk engines; breed is never a ranking input."""
    today = today or date.today()
    walk_time = walk_time or time(12, 0)
    matches: list[dict[str, Any]] = []
    for dog in dogs:
        heat = calculate_heat_risk(dog, environment, today=today)
        surface_result = calculate_surface_risk(surface, environment, walk_time) if surface else None
        score = max(heat["score"], surface_result["score"] if surface_result else 0)
        duration_cap = recommended_walk_duration(dog, score, today=today)
        planned_duration = min(available_minutes, duration_cap)
        suitable = score < 50 and planned_duration > 0
        why = f"Estimated { _level(score).lower() } risk ({score}/100) with a cautious {planned_duration}-minute walk cap." if suitable else f"Not recommended now: estimated {_level(score).lower()} risk ({score}/100) or no safe duration cap."
        matches.append({"dog_id": str(dog.id), "dog_name": dog.name, "estimated_risk": score, "status": _level(score), "recommended_duration_minutes": planned_duration, "duration_cap_minutes": duration_cap, "suitable": suitable, "why": why, "main_factors": heat["main_factors"], "heat_risk": heat, "surface_risk": surface_result})
    matches.sort(key=lambda item: (not item["suitable"], item["estimated_risk"], -item["recommended_duration_minutes"], item["dog_name"].lower()))
    suitable = [match for match in matches if match["suitable"]]
    avoided = [match for match in matches if not match["suitable"]]
    best = suitable[0] if suitable else None
    message = f"{best['dog_name']} is the best match for your available time." if best else "No dog is a suitable walk match under the current estimated conditions. Consider postponing outdoor walks."
    return {"best_match": best, "ranked_matches": matches, "avoid": avoided, "message": message, "disclaimer": "This is a cautious estimated matching aid, not veterinary advice or a guarantee of safety. Do not walk a dog showing heat-stress signs; monitor every dog closely and stop if concerned."}
