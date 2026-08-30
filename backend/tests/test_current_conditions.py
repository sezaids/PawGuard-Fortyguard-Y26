from app.services import current_conditions


def test_current_environment_uses_fortyguard_heatmap_temperature(monkeypatch):
    calls = []
    monkeypatch.setattr(current_conditions.fortyguard_service, "submit_heatmap", lambda payload: calls.append(("heatmap", payload)) or {"data": {"activity_id": "map"}})
    monkeypatch.setattr(current_conditions.fortyguard_service, "submit_environment", lambda payload: calls.append(("environment", payload)) or {"data": {"activity_id": "env"}})
    monkeypatch.setattr(current_conditions.fortyguard_service, "wait_for_completion", lambda activity_id, _: {"data": {"status": "Completed", "result": {"stats_data": {"Temperature_stats": {"Mean": 28.5}}}}} if activity_id == "map" else {"data": {"status": "Completed", "result": {"locations": [{"temperature": 28.5, "parameters": {"apparent_temperature_celsius": [30], "relative_humidity_percent": [55]}, "solar_irradiance": {"clear_sky": {"ghi": 400}}}]}}})
    environment = current_conditions.current_environment(40.7, -74.0, 1)
    assert environment["temperature_celsius"] == 28.5
    assert calls[1][1]["temperature"] == 28.5
