"""Configurable deterministic rules for estimated outdoor paw-surface risk.

This estimates relative exposure; it does not measure or infer exact pavement temperature.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SurfaceRiskRules:
    surface_points: dict[str, int] | None = None
    temperature_bands: tuple[tuple[float, int], ...] = ((20, 0), (25, 10), (30, 23), (35, 38), (99, 52))
    solar_moderate_wm2: float = 250
    solar_high_wm2: float = 600
    midday_start_hour: int = 10
    midday_end_hour: int = 16

    def __post_init__(self) -> None:
        object.__setattr__(self, "surface_points", self.surface_points or {"grass": 0, "soil_dirt": 8, "sand": 13, "concrete": 19, "asphalt": 27})


SURFACE_RISK_RULES = SurfaceRiskRules()
