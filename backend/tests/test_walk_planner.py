from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.services.walk_planner import forecast_result_diagnostics, forecast_temperature_from_result, rank_walk_windows
from app.api.routes.walk_planner import small_square_aoi


def dog(**overrides):
    defaults = dict(date_of_birth=date(2022, 1, 1), body_size="medium", weight_kg=18, coat_color="cream", coat_length="short", brachycephalic=False, activity_level="moderate", fitness_level="high")
    return SimpleNamespace(**(defaults | overrides))


def test_planner_ranks_coolest_interval_first():
    plan = rank_walk_windows(dog(), [{"time": datetime(2026, 8, 30, 9, tzinfo=timezone.utc), "temperature_celsius": 20}, {"time": datetime(2026, 8, 30, 15, tzinfo=timezone.utc), "temperature_celsius": 33}], today=date(2026, 8, 30))
    assert plan["best_window"]["forecast_temperature_celsius"] == 20
    assert plan["best_window"]["recommended_duration_minutes"] > 20


def test_surface_can_make_warm_window_unsuitable():
    plan = rank_walk_windows(dog(), [{"time": datetime(2026, 8, 30, 13, tzinfo=timezone.utc), "temperature_celsius": 38}], surface="asphalt", today=date(2026, 8, 30))
    assert plan["best_window"] is None
    assert plan["all_windows"][0]["recommended_duration_minutes"] == 0


def test_no_safe_window_explains_unavailability():
    plan = rank_walk_windows(dog(), [{"time": datetime(2026, 8, 30, 12, tzinfo=timezone.utc), "temperature_celsius": 38}], today=date(2026, 8, 30))
    assert plan["best_window"] is None
    assert "No lower-risk" in plan["message"]


def test_heatmap_temperature_statistic_is_read():
    assert forecast_temperature_from_result({"stats_data": {"Temperature_stats": {"Mean": 28.4}}}) == 28.4


def test_heatmap_temperature_accepts_provider_casing_variants():
    assert forecast_temperature_from_result({"stats_data": {"temperature": {"average": "28.4"}}}) == 28.4


def test_heatmap_temperature_uses_real_temperature_tiles_when_stats_are_absent():
    result = {"map_data": {"type": "FeatureCollection", "features": [
        {"properties": {"temperature": 28}},
        {"properties": {"Temperature": 30}},
    ]}}
    assert forecast_temperature_from_result(result) == 29


def test_heatmap_temperature_normalizes_confirmed_completed_provider_shape():
    # Sanitized structure from a completed FortyGuard heatmap activity. Values
    # are fixtures only; production values are never logged or manufactured.
    activity = {
        "data": {
            "status": "Completed",
            "result": {
                "stats_data": {"temperature_stats": {"minimum": 18.0, "maximum": 24.0, "mean": 21.5, "standard_deviation": 1.2}},
                "map_data": {"type": "FeatureCollection", "features": [
                    {"type": "Feature", "properties": {"tile_id": 1, "average_temperature": 21.5, "min_temperature": 18.0, "max_temperature": 24.0}}
                ]},
            },
        }
    }
    assert forecast_temperature_from_result(activity) == 21.5
    diagnostics = forecast_result_diagnostics(activity)
    assert diagnostics["stats_keys"] == ["temperature_stats"]
    assert diagnostics["first_feature_property_keys"] == ["average_temperature", "max_temperature", "min_temperature", "tile_id"]


def test_heatmap_temperature_uses_confirmed_average_temperature_tile_name():
    activity = {"data": {"result": {"map_data": {"features": [
        {"properties": {"average_temperature": 20.0}},
        {"properties": {"average_temperature": 22.0}},
    ]}}}}
    assert forecast_temperature_from_result(activity) == 21.0


def test_heatmap_temperature_accepts_async_route_completed_data_envelope():
    completed_data = {"status": "Completed", "result": {"stats_data": {"temperature_stats": {"mean": 19.5}}}}
    assert forecast_temperature_from_result(completed_data) == 19.5


def test_forecast_aoi_uses_heatmap_tile_footprint_not_empty_small_cell_area():
    aoi = small_square_aoi(34.0522, -118.2437)
    ring = aoi["features"][0]["geometry"]["coordinates"][0]
    assert abs((ring[1][0] - ring[0][0]) - 0.012) < 1e-9
    assert abs((ring[2][1] - ring[1][1]) - 0.012) < 1e-9
