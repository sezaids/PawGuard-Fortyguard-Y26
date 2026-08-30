"""Configurable, deterministic PawGuard heat-risk scoring rules.

These weights are product safety heuristics, not medical thresholds or a diagnosis.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskRules:
    apparent_temperature_bands: tuple[tuple[float, int], ...] = ((18, 0), (22, 8), (26, 18), (30, 32), (34, 48), (99, 60))
    humidity_threshold: float = 60
    humidity_max_points: int = 12
    solar_moderate_wm2: float = 250
    solar_high_wm2: float = 600
    dark_coat_points: int = 7
    thick_coat_points: dict[str, int] | None = None
    body_size_points: dict[str, int] | None = None
    age_points: dict[str, int] | None = None
    activity_points: dict[str, int] | None = None
    fitness_points: dict[str, int] | None = None
    brachycephalic_points: int = 16

    def __post_init__(self) -> None:
        object.__setattr__(self, "thick_coat_points", self.thick_coat_points or {"medium": 1, "long": 3, "double": 4})
        object.__setattr__(self, "body_size_points", self.body_size_points or {"small": 6, "medium": 2, "large": 1, "giant": 4})
        object.__setattr__(self, "age_points", self.age_points or {"puppy": 8, "senior": 10})
        object.__setattr__(self, "activity_points", self.activity_points or {"moderate": 2, "high": 5})
        object.__setattr__(self, "fitness_points", self.fitness_points or {"low": 7, "average": 2})


RISK_RULES = RiskRules()
