"""Deterministic configuration for the multi-dog daily walk scheduler."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DailySchedulerRules:
    safe_score_max: int = 50
    minimum_walk_minutes: int = 10
    maximum_forecast_hours: int = 12


DAILY_SCHEDULER_RULES = DailySchedulerRules()
