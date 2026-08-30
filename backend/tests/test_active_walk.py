from datetime import date, time
from types import SimpleNamespace

from app.services.active_walk import active_walk_summary


def dog(**overrides):
    defaults = dict(date_of_birth=date(2022, 1, 1), body_size="medium", weight_kg=18, coat_color="cream", coat_length="short", brachycephalic=False, activity_level="moderate", fitness_level="high")
    return SimpleNamespace(**(defaults | overrides))


def test_active_walk_returns_shared_risk_engines_and_duration_limit():
    result = active_walk_summary(dog(), {"temperature_celsius": 22, "apparent_temperature_celsius": 22, "relative_humidity_percent": 45, "solar_ghi_wm2": 100}, "grass", time(8), today=date(2026, 8, 30))
    assert result["recommended_duration_minutes"] > 0
    assert result["heat_risk"]["status"] in {"Low", "Moderate"}
    assert result["surface_risk"]["level"] == "Low"


def test_active_walk_high_risk_tells_user_to_end_outdoor_walk():
    result = active_walk_summary(dog(brachycephalic=True, coat_color="black", coat_length="double", fitness_level="low"), {"temperature_celsius": 38, "apparent_temperature_celsius": 39, "relative_humidity_percent": 75, "solar_ghi_wm2": 800}, "asphalt", time(13), today=date(2026, 8, 30))
    assert result["recommended_duration_minutes"] == 0
    assert "End the outdoor walk" in result["reminders"][0]
