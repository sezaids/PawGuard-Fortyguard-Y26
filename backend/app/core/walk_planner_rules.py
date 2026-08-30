"""Configurable deterministic rules for upcoming walk-window ranking and duration."""
from dataclasses import dataclass


@dataclass(frozen=True)
class WalkPlannerRules:
    default_horizon_hours: int = 12
    default_interval_hours: int = 3
    duration_base_minutes: int = 35
    activity_minutes: dict[str, int] | None = None
    fitness_minutes: dict[str, int] | None = None
    high_risk_cap_minutes: int = 10
    moderate_risk_cap_minutes: int = 20

    def __post_init__(self) -> None:
        object.__setattr__(self, "activity_minutes", self.activity_minutes or {"low": 0, "moderate": 5, "high": 10})
        object.__setattr__(self, "fitness_minutes", self.fitness_minutes or {"low": -10, "average": 0, "high": 5})


WALK_PLANNER_RULES = WalkPlannerRules()
