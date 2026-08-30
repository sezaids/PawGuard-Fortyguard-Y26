"""Cautious, deterministic status summary for a currently active walk."""
from __future__ import annotations

from datetime import date, time
from typing import Any

from app.models.dog import Dog
from app.services.heat_risk import calculate_heat_risk
from app.services.surface_risk import calculate_surface_risk
from app.services.walk_planner import recommended_walk_duration


def active_walk_summary(dog: Dog, environment: dict[str, float | None], surface: str, walk_time: time, today: date | None = None) -> dict[str, Any]:
    heat = calculate_heat_risk(dog, environment, today=today)
    surface_result = calculate_surface_risk(surface, environment, walk_time)
    combined = max(heat["score"], surface_result["score"])
    duration = recommended_walk_duration(dog, combined, today=today)
    if combined >= 75:
        reminders = ["End the outdoor walk and move to a cooler area now.", "Offer water if your dog is alert and able to drink.", "Watch closely for heat-stress signs; seek urgent veterinary advice if you are concerned."]
        caution = "Very high estimated risk: PawGuard does not recommend continuing an outdoor walk."
    elif combined >= 50:
        reminders = ["Keep this essential outing very brief and in shade.", "Pause now for water and a calm rest.", "Avoid hot surfaces and stop if your dog seems distressed."]
        caution = "High estimated risk: shorten or end the walk now."
    else:
        reminders = ["Offer water and a quiet shade break regularly.", "Keep the pace easy and watch for changes in breathing or behavior.", "Check the surface often and turn back early if conditions worsen."]
        caution = "Conditions are an estimate; end the walk early whenever your dog seems uncomfortable."
    return {"heat_risk": heat, "surface_risk": surface_result, "recommended_duration_minutes": duration, "reminders": reminders, "caution": caution, "disclaimer": "This Active Walk summary is a cautious planning aid, not veterinary advice or a diagnosis. Environmental estimates can change quickly; stop the walk and contact a veterinarian promptly if you are concerned about your dog."}
