from datetime import time

from app.services.surface_risk import calculate_surface_risk


def test_grass_in_mild_shaded_conditions_is_low():
    result = calculate_surface_risk("grass", {"temperature_celsius": 19, "apparent_temperature_celsius": 19, "solar_ghi_wm2": 80}, time(8, 0))
    assert result["level"] == "Low"
    assert result["score"] < 25


def test_asphalt_at_midday_in_high_sun_is_very_high():
    result = calculate_surface_risk("asphalt", {"temperature_celsius": 35, "apparent_temperature_celsius": 37, "solar_ghi_wm2": 780}, time(13, 0))
    assert result["level"] == "Very High"
    assert result["score"] >= 75


def test_sand_in_warm_sun_is_high_and_suggests_alternatives():
    result = calculate_surface_risk("sand", {"temperature_celsius": 31, "apparent_temperature_celsius": 32, "solar_ghi_wm2": 400}, time(11, 30))
    assert result["level"] == "High"
    assert "grass" in " ".join(result["safer_alternatives"]).lower()
