"""Deterministic, non-overlapping allocation of real forecast intervals to dogs."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.core.daily_scheduler_rules import DAILY_SCHEDULER_RULES, DailySchedulerRules
from app.models.dog import Dog
from app.services.walk_planner import rank_walk_windows


def _fits_availability(start: datetime, duration_minutes: int, availability: list[tuple[datetime, datetime]]) -> bool:
    end = start + timedelta(minutes=duration_minutes)
    return any(block_start <= start and end <= block_end for block_start, block_end in availability)


def _overlaps(start: datetime, duration_minutes: int, scheduled: list[dict[str, Any]]) -> bool:
    end = start + timedelta(minutes=duration_minutes)
    return any(start < item["_end"] and end > item["_start"] for item in scheduled)


def build_daily_schedule(
    dogs: list[Dog],
    intervals: list[dict[str, Any]],
    availability: list[tuple[datetime, datetime]],
    surface: str | None = None,
    rules: DailySchedulerRules = DAILY_SCHEDULER_RULES,
    today: date | None = None,
) -> dict[str, Any]:
    """Assign one safe forecast-backed slot per dog, never inventing a window."""
    today = today or date.today()
    candidates: list[tuple[Dog, list[dict[str, Any]]]] = []
    unscheduled: list[dict[str, str]] = []

    for dog in dogs:
        plan = rank_walk_windows(dog, intervals, surface=surface, today=today)
        options = []
        for window in plan["all_windows"]:
            start = datetime.fromisoformat(window["start"])
            duration = window["recommended_duration_minutes"]
            if (
                window["estimated_risk"] < rules.safe_score_max
                and duration >= rules.minimum_walk_minutes
                and _fits_availability(start, duration, availability)
            ):
                options.append({**window, "_start": start, "_end": start + timedelta(minutes=duration)})
        if options:
            options.sort(key=lambda option: (option["estimated_risk"], option["_start"]))
            candidates.append((dog, options))
        else:
            unscheduled.append({"dog_id": str(dog.id), "dog_name": dog.name, "reason": "No lower-risk forecast interval fits this dog’s available time blocks and recommended duration."})

    # Dogs with less tolerance (higher best available risk) get first choice of the
    # safer windows. A tie gives the dog with fewer options priority.
    candidates.sort(key=lambda item: (-item[1][0]["estimated_risk"], len(item[1]), item[0].name.lower()))
    scheduled: list[dict[str, Any]] = []
    for dog, options in candidates:
        option = next((item for item in options if not _overlaps(item["_start"], item["recommended_duration_minutes"], scheduled)), None)
        if option is None:
            unscheduled.append({"dog_id": str(dog.id), "dog_name": dog.name, "reason": "A suitable forecast interval exists, but it conflicts with a safer walk already assigned to another dog."})
            continue
        scheduled.append({
            "dog_id": str(dog.id), "dog_name": dog.name, "start": option["start"], "end": option["_end"].isoformat(),
            "duration_minutes": option["recommended_duration_minutes"], "estimated_risk": option["estimated_risk"],
            "status": option["status"], "forecast_temperature_celsius": option["forecast_temperature_celsius"],
            "explanation": f"Assigned this lower-risk available interval for {dog.name}. Estimated {option['status'].lower()} risk ({option['estimated_risk']}/100) supports a cautious {option['recommended_duration_minutes']}-minute walk; heat-sensitive dogs are considered first.",
            "heat_risk": option["heat_risk"], "surface_risk": option["surface_risk"], "_start": option["_start"], "_end": option["_end"],
        })

    scheduled.sort(key=lambda item: item["_start"])
    for item in scheduled:
        item.pop("_start")
        item.pop("_end")
    message = f"Scheduled {len(scheduled)} of {len(dogs)} dog(s) using completed FortyGuard forecast intervals." if scheduled else "No suitable outdoor walk slot is available in the completed forecast intervals and the time blocks you supplied."
    return {"scheduled": scheduled, "unscheduled": unscheduled, "message": message, "disclaimer": "This is a cautious estimated schedule, not medical advice or a guarantee of safety. It only uses completed FortyGuard forecast intervals; conditions can change, so monitor every dog and shorten or stop a walk if concerned."}
