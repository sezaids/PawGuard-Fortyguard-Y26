from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.active_walk import active_walk_summary
from app.schemas.active_walk import ActiveWalkStatusResponse
from app.api.routes import active_walk
from app.api.routes.active_walk import unavailable_active_walk_status
from app.schemas.active_walk import ActiveWalkStatusRequest


def dog(**overrides):
    defaults = dict(date_of_birth=date(2022, 1, 1), body_size="medium", weight_kg=18, coat_color="cream", coat_length="short", brachycephalic=False, activity_level="moderate", fitness_level="high")
    return SimpleNamespace(**(defaults | overrides))


def test_active_walk_returns_shared_risk_engines_and_duration_limit():
    result = active_walk_summary(dog(), {"temperature_celsius": 22, "apparent_temperature_celsius": 22, "relative_humidity_percent": 45, "solar_ghi_wm2": 100}, "grass", time(8), today=date(2026, 8, 30))
    response = ActiveWalkStatusResponse.model_validate(result)
    assert result["recommended_duration_minutes"] > 0
    assert result["heat_risk"]["status"] in {"Low", "Moderate"}
    assert result["surface_risk"]["level"] == "Low"
    assert response.heat_risk.score == result["heat_risk"]["score"]


def test_active_walk_high_risk_tells_user_to_end_outdoor_walk():
    result = active_walk_summary(dog(brachycephalic=True, coat_color="black", coat_length="double", fitness_level="low"), {"temperature_celsius": 38, "apparent_temperature_celsius": 39, "relative_humidity_percent": 75, "solar_ghi_wm2": 800}, "asphalt", time(13), today=date(2026, 8, 30))
    assert result["recommended_duration_minutes"] == 0
    assert "End the outdoor walk" in result["reminders"][0]


def test_active_walk_provider_failure_returns_a_structured_no_live_data_response():
    response = ActiveWalkStatusResponse.model_validate(unavailable_active_walk_status("FortyGuard did not respond before the request timed out."))
    assert response.state == "unavailable"
    assert response.heat_risk is None
    assert response.surface_risk is None
    assert response.recommended_duration_minutes is None
    assert "timed out" in response.unavailable_reason


@pytest.mark.parametrize("status_code, detail", [
    (504, "FortyGuard did not respond before the request timed out."),
    (502, "FortyGuard could not complete the current environmental analysis."),
    (202, "FortyGuard is still processing this location. Please retry shortly."),
])
def test_active_walk_converts_provider_delay_or_failure_to_no_live_data(monkeypatch, status_code, detail):
    dog_id = uuid4()
    received_wait_seconds = []
    monkeypatch.setattr(active_walk, "owned_dog", lambda *_: dog())
    def unavailable_environment(*args):
        received_wait_seconds.append(args[-1])
        raise HTTPException(status_code=status_code, detail=detail)

    monkeypatch.setattr(active_walk, "current_environment", unavailable_environment)
    response = active_walk.current_active_walk_status(
        dog_id,
        ActiveWalkStatusRequest(latitude=44.7973, longitude=-106.9562, surface="grass"),
        SimpleNamespace(id=uuid4()),
        SimpleNamespace(),
    )
    assert response["state"] == "unavailable"
    assert response["unavailable_reason"] == detail
    assert response["heat_risk"] is None
    assert received_wait_seconds == [8]


def test_active_walk_analysis_polls_existing_provider_jobs_without_duplicates(monkeypatch):
    active_walk._active_walk_analyses.clear()
    owner_id = uuid4()
    submitted = []
    monkeypatch.setattr(active_walk, "owned_dog", lambda *_: dog())
    monkeypatch.setattr(active_walk.fortyguard_service, "submit_heatmap", lambda *_, **__: submitted.append("heatmap") or {"data": {"activity_id": "heat-job"}})
    monkeypatch.setattr(active_walk.fortyguard_service, "submit_environment", lambda *_, **__: submitted.append("environment") or {"data": {"activity_id": "environment-job"}})
    provider_results = iter([
        {"data": {"status": "Processing"}},
        {"data": {"status": "Completed", "result": {"stats_data": {"Temperature_stats": {"Mean": 28.5}}}}},
        {"data": {"status": "Completed", "result": {"locations": [{"temperature": 28.5, "parameters": {"apparent_temperature_celsius": [30], "relative_humidity_percent": [55]}, "solar_irradiance": {"clear_sky": {"ghi": 400}}}]}}},
    ])
    monkeypatch.setattr(active_walk.fortyguard_service, "status", lambda *_, **__: next(provider_results))
    request = ActiveWalkStatusRequest(latitude=44.7973, longitude=-106.9562, surface="grass")
    user = SimpleNamespace(id=owner_id)
    started = active_walk.start_active_walk_analysis(uuid4(), request, user, SimpleNamespace())
    assert started["state"] == "processing"
    analysis_id = started["analysis_id"]
    assert active_walk.poll_active_walk_analysis(analysis_id, user, SimpleNamespace())["stage"] == "heatmap"
    assert active_walk.poll_active_walk_analysis(analysis_id, user, SimpleNamespace())["stage"] == "environment"
    completed = active_walk.poll_active_walk_analysis(analysis_id, user, SimpleNamespace())
    assert completed["state"] == "completed"
    assert completed["result"]["state"] == "available"
    assert completed["result"]["heat_risk"]["score"] >= 0
    assert submitted == ["heatmap", "environment"]


def test_active_walk_analysis_reports_provider_failure_without_a_risk_estimate(monkeypatch):
    active_walk._active_walk_analyses.clear()
    owner_id = uuid4()
    monkeypatch.setattr(active_walk, "owned_dog", lambda *_: dog())
    monkeypatch.setattr(active_walk.fortyguard_service, "submit_heatmap", lambda *_, **__: {"data": {"activity_id": "heat-job"}})
    monkeypatch.setattr(active_walk.fortyguard_service, "status", lambda *_, **__: {"data": {"status": "Failed"}})
    started = active_walk.start_active_walk_analysis(uuid4(), ActiveWalkStatusRequest(latitude=44.7973, longitude=-106.9562, surface="grass"), SimpleNamespace(id=owner_id), SimpleNamespace())
    unavailable = active_walk.poll_active_walk_analysis(started["analysis_id"], SimpleNamespace(id=owner_id), SimpleNamespace())
    assert unavailable["state"] == "unavailable"
    assert unavailable["heat_risk"] is None
