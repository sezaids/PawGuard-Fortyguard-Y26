from types import SimpleNamespace

from app.services.walk_history import build_walk_summary


def walk(minutes, risk="Low"):
    return SimpleNamespace(duration_minutes=minutes, heat_risk_status=risk)


def test_walk_summary_returns_useful_totals_and_latest_risk():
    result = build_walk_summary([walk(20, "Moderate"), walk(10)])
    assert result["total_walks"] == 2
    assert result["total_minutes"] == 30
    assert result["average_duration_minutes"] == 15
    assert result["latest_heat_risk_status"] == "Moderate"


def test_walk_summary_has_clear_empty_state():
    result = build_walk_summary([])
    assert result["total_walks"] == 0
    assert "No completed walks" in result["message"]
