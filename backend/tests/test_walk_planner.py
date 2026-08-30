from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.services.walk_planner import forecast_temperature_from_result, rank_walk_windows


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
