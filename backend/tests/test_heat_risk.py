from datetime import date
from types import SimpleNamespace

from app.services.heat_risk import calculate_heat_risk


def dog(**overrides):
    defaults = dict(date_of_birth=date(2022, 1, 1), body_size="medium", weight_kg=18, coat_color="cream", coat_length="short", brachycephalic=False, activity_level="low", fitness_level="high")
    return SimpleNamespace(**(defaults | overrides))


def test_mild_conditions_are_low_risk():
    result = calculate_heat_risk(dog(), {"temperature_celsius": 18, "apparent_temperature_celsius": 18, "relative_humidity_percent": 45, "solar_ghi_wm2": 100}, today=date(2026, 8, 30))
    assert result["score"] < 25
    assert result["status"] == "Low"


def test_hot_humid_brachycephalic_dog_is_very_high_risk():
    result = calculate_heat_risk(dog(date_of_birth=date(2016, 1, 1), body_size="small", weight_kg=10, coat_color="black", coat_length="double", brachycephalic=True, activity_level="high", fitness_level="low"), {"temperature_celsius": 35, "apparent_temperature_celsius": 38, "relative_humidity_percent": 85, "solar_ghi_wm2": 750}, today=date(2026, 8, 30))
    assert result["score"] >= 75
    assert result["status"] == "Very High"
    assert result["main_factors"][0]["factor"] == "Apparent temperature"


def test_warm_conditions_with_dark_long_coat_are_high_risk():
    result = calculate_heat_risk(dog(coat_color="dark brown", coat_length="long", body_size="giant", activity_level="moderate", fitness_level="average"), {"temperature_celsius": 31, "apparent_temperature_celsius": 32, "relative_humidity_percent": 70, "solar_ghi_wm2": 400}, today=date(2026, 8, 30))
    assert 50 <= result["score"] < 75
    assert result["status"] == "High"
