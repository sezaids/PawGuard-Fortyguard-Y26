"""Pure, explainable dog heat-risk calculation; no model or provider calls live here."""
from __future__ import annotations

from datetime import date
from typing import Any

from app.core.risk_rules import RISK_RULES, RiskRules
from app.models.dog import Dog

_DARK_COLORS = {"black", "dark brown", "brown", "dark gray", "dark grey", "dark", "chocolate", "brindle"}


def _first(value: Any, fallback: float | None = None) -> float | None:
    if isinstance(value, list) and value:
        value = value[0]
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def extract_environment(result: dict[str, Any], supplied_temperature: float | None = None) -> dict[str, float | None]:
    """Extract only documented FortyGuard completed env_params fields."""
    location = (result.get("locations") or [{}])[0]
    parameters = location.get("parameters") or {}
    irradiance = (location.get("solar_irradiance") or {}).get("clear_sky") or {}
    ambient = _first(location.get("temperature"), supplied_temperature)
    apparent = _first(parameters.get("apparent_temperature_celsius"), ambient)
    return {
        "temperature_celsius": ambient,
        "apparent_temperature_celsius": apparent,
        "relative_humidity_percent": _first(parameters.get("relative_humidity_percent")),
        "solar_ghi_wm2": _first(irradiance.get("ghi")),
    }


def _age_category(dob: date | None, today: date) -> str | None:
    if not dob:
        return None
    years = (today - dob).days / 365.25
    if years < 1:
        return "puppy"
    if years >= 7:
        return "senior"
    return None


def calculate_heat_risk(dog: Dog, environment: dict[str, float | None], rules: RiskRules = RISK_RULES, today: date | None = None) -> dict[str, Any]:
    """Calculate a 0–100 estimate and trace every contributing point value."""
    factors: list[dict[str, Any]] = []

    def add(label: str, points: int, detail: str) -> None:
        if points:
            factors.append({"factor": label, "points": points, "detail": detail})

    apparent = environment.get("apparent_temperature_celsius") or environment.get("temperature_celsius") or 0
    for limit, points in rules.apparent_temperature_bands:
        if apparent <= limit:
            add("Apparent temperature", points, f"{apparent:.1f}°C")
            break
    humidity = environment.get("relative_humidity_percent")
    if humidity is not None and humidity > rules.humidity_threshold:
        add("Humidity", min(rules.humidity_max_points, round((humidity - rules.humidity_threshold) / 3)), f"{humidity:.0f}%")
    ghi = environment.get("solar_ghi_wm2")
    if ghi is not None:
        add("Solar exposure", 10 if ghi >= rules.solar_high_wm2 else 5 if ghi >= rules.solar_moderate_wm2 else 0, f"{ghi:.0f} W/m² clear-sky GHI")

    age = _age_category(dog.date_of_birth, today or date.today())
    if age:
        add("Age", rules.age_points[age], age)
    add("Body size", rules.body_size_points.get(dog.body_size, 0), dog.body_size)
    if dog.weight_kg and dog.weight_kg >= 35:
        add("Weight", 3, f"{dog.weight_kg:g} kg")
    if dog.coat_color and dog.coat_color.strip().lower() in _DARK_COLORS:
        add("Dark coat color", rules.dark_coat_points, dog.coat_color)
    add("Coat length / thickness", rules.thick_coat_points.get(dog.coat_length, 0), dog.coat_length)
    if dog.brachycephalic:
        add("Short-nosed (brachycephalic)", rules.brachycephalic_points, "reduced cooling efficiency")
    add("Activity level", rules.activity_points.get(dog.activity_level, 0), dog.activity_level)
    add("Fitness level", rules.fitness_points.get(dog.fitness_level, 0), dog.fitness_level)

    score = min(100, sum(item["points"] for item in factors))
    if score < 25:
        status, recommendation = "Low", "Conditions appear comparatively mild. A short, supervised walk may be reasonable with water and close observation."
    elif score < 50:
        status, recommendation = "Moderate", "Choose a short, shaded, low-intensity walk. Bring water and stop at the first sign of overheating."
    elif score < 75:
        status, recommendation = "High", "Avoid a routine outdoor walk now. If essential, keep it very brief, shaded, and low intensity with water available."
    else:
        status, recommendation = "Very High", "Do not take a planned walk now. Keep your dog cool indoors and seek urgent veterinary advice if heat-stress signs appear."
    return {"score": score, "status": status, "recommendation": recommendation, "main_factors": sorted(factors, key=lambda item: item["points"], reverse=True)[:5], "environment": environment, "disclaimer": "This is a cautious estimated risk score, not a veterinary diagnosis. Watch your dog closely and contact a veterinarian promptly if you notice heat-stress signs."}
