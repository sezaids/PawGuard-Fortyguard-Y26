from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.routes import daily_scheduler
from app.schemas.daily_scheduler import AvailabilityBlock, DailyScheduleRequest


def test_daily_schedule_analysis_reuses_jobs_across_polls(monkeypatch):
    daily_scheduler._schedule_analyses.clear()
    owner_id = uuid4()
    now = datetime(2026, 8, 30, 8, tzinfo=timezone.utc)
    payload = DailyScheduleRequest(
        latitude=44.7973,
        longitude=-106.9562,
        availability=[AvailabilityBlock(start=now, end=now.replace(hour=10))],
    )
    dog = SimpleNamespace(id=uuid4(), name="Luna")
    monkeypatch.setattr(daily_scheduler, "_schedule_inputs", lambda *_: ([dog], [(now, now.replace(hour=10))], [now, now.replace(hour=9)]))
    submitted = []
    monkeypatch.setattr(daily_scheduler.fortyguard_service, "submit_heatmap", lambda *_: submitted.append(1) or {"data": {"activity_id": f"job-{len(submitted)}"}})
    statuses = iter([
        {"data": {"status": "Processing"}},
        {"data": {"status": "Completed", "result": {"stats_data": {"temperature_stats": {"mean": 20}}}}},
        {"data": {"status": "Completed", "result": {"map_data": {"type": "FeatureCollection", "features": [{"properties": {"average_temperature": 21}}]}}}},
    ])
    monkeypatch.setattr(daily_scheduler.fortyguard_service, "status", lambda *_, **__: next(statuses))
    monkeypatch.setattr(daily_scheduler, "build_daily_schedule", lambda dogs, intervals, availability, surface: {"scheduled": [], "unscheduled": [], "message": "Ready", "disclaimer": "Planning guidance only."})

    class ImmediateThread:
        def __init__(self, target, args, daemon): self.target, self.args = target, args
        def start(self): self.target(*self.args)

    monkeypatch.setattr(daily_scheduler, "Thread", ImmediateThread)
    user = SimpleNamespace(id=owner_id)
    db = SimpleNamespace(scalars=lambda _: [dog])
    started = daily_scheduler.start_daily_schedule_analysis(payload, user, db)
    analysis_id = started["analysis_id"]
    assert daily_scheduler.poll_daily_schedule_analysis(analysis_id, user, db)["state"] == "processing"
    assert daily_scheduler.poll_daily_schedule_analysis(analysis_id, user, db)["state"] == "processing"
    completed = daily_scheduler.poll_daily_schedule_analysis(analysis_id, user, db)
    assert completed["state"] == "completed"
    assert len(submitted) == 2
