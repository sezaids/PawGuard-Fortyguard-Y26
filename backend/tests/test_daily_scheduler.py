from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.daily_scheduler import build_daily_schedule


def dog(name, **overrides):
    defaults = dict(id=uuid4(), name=name, date_of_birth=date(2022, 1, 1), body_size="medium", weight_kg=18, coat_color="cream", coat_length="short", brachycephalic=False, activity_level="moderate", fitness_level="high")
    return SimpleNamespace(**(defaults | overrides))


def interval(hour, temperature=18):
    return {"time": datetime(2026, 8, 30, hour, tzinfo=timezone.utc), "temperature_celsius": temperature}


def test_scheduler_assigns_non_overlapping_slots_for_multiple_dogs():
    result = build_daily_schedule([dog("Luna"), dog("Milo")], [interval(8), interval(9)], [(datetime(2026, 8, 30, 8, tzinfo=timezone.utc), datetime(2026, 8, 30, 10, tzinfo=timezone.utc))], today=date(2026, 8, 30))
    assert len(result["scheduled"]) == 2
    assert result["scheduled"][0]["end"] <= result["scheduled"][1]["start"]


def test_scheduler_prioritizes_more_heat_sensitive_dog_for_earlier_safe_slot():
    sensitive = dog("Sensitive", brachycephalic=True, coat_color="black", coat_length="double", fitness_level="low")
    result = build_daily_schedule([dog("Robust"), sensitive], [interval(8), interval(9)], [(datetime(2026, 8, 30, 8, tzinfo=timezone.utc), datetime(2026, 8, 30, 10, tzinfo=timezone.utc))], today=date(2026, 8, 30))
    assert result["scheduled"][0]["dog_name"] == "Sensitive"


def test_scheduler_marks_dog_unscheduled_when_limited_block_cannot_fit_duration():
    result = build_daily_schedule([dog("Luna")], [interval(8)], [(datetime(2026, 8, 30, 8, tzinfo=timezone.utc), datetime(2026, 8, 30, 8, 20, tzinfo=timezone.utc))], today=date(2026, 8, 30))
    assert result["scheduled"] == []
    assert result["unscheduled"][0]["dog_name"] == "Luna"


def test_scheduler_marks_conflicting_dog_unscheduled_instead_of_overlapping():
    result = build_daily_schedule([dog("Luna"), dog("Milo")], [interval(8)], [(datetime(2026, 8, 30, 8, tzinfo=timezone.utc), datetime(2026, 8, 30, 9, tzinfo=timezone.utc))], today=date(2026, 8, 30))
    assert len(result["scheduled"]) == 1
    assert len(result["unscheduled"]) == 1
    assert "conflicts" in result["unscheduled"][0]["reason"]


def test_scheduler_returns_no_safe_slot_when_forecast_is_hot():
    result = build_daily_schedule([dog("Luna")], [interval(13, 38)], [(datetime(2026, 8, 30, 13, tzinfo=timezone.utc), datetime(2026, 8, 30, 14, tzinfo=timezone.utc))], surface="asphalt", today=date(2026, 8, 30))
    assert result["scheduled"] == []
    assert "No lower-risk" in result["unscheduled"][0]["reason"]
