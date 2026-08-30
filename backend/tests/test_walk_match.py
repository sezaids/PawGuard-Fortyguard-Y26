from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

from app.services.walk_match import match_dogs_for_walk


def dog(name, **overrides):
    defaults = dict(id=uuid4(), name=name, date_of_birth=date(2022, 1, 1), body_size="medium", weight_kg=18, coat_color="cream", coat_length="short", brachycephalic=False, activity_level="moderate", fitness_level="high")
    return SimpleNamespace(**(defaults | overrides))


def test_walk_match_ranks_lower_risk_dog_first():
    dogs = [dog("Baxter", brachycephalic=True, coat_color="black", coat_length="double", fitness_level="low"), dog("Luna")]
    result = match_dogs_for_walk(dogs, {"temperature_celsius": 29, "apparent_temperature_celsius": 30, "relative_humidity_percent": 65, "solar_ghi_wm2": 300}, 30, today=date(2026, 8, 30), walk_time=time(9))
    assert result["best_match"]["dog_name"] == "Luna"
    assert result["ranked_matches"][0]["dog_name"] == "Luna"


def test_surface_and_heat_can_leave_no_dog_suitable():
    dogs = [dog("Milo"), dog("Poppy", brachycephalic=True)]
    result = match_dogs_for_walk(dogs, {"temperature_celsius": 38, "apparent_temperature_celsius": 38, "relative_humidity_percent": 70, "solar_ghi_wm2": 800}, 15, "asphalt", time(13), today=date(2026, 8, 30))
    assert result["best_match"] is None
    assert len(result["avoid"]) == 2


def test_available_time_caps_recommendation():
    result = match_dogs_for_walk([dog("Luna")], {"temperature_celsius": 18, "apparent_temperature_celsius": 18, "relative_humidity_percent": 40, "solar_ghi_wm2": 100}, 15, today=date(2026, 8, 30), walk_time=time(8))
    assert result["best_match"]["recommended_duration_minutes"] == 15
