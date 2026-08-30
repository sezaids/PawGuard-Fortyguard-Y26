"""Small, source-preserving summaries over persisted completed walks."""
from __future__ import annotations

from typing import Any


def build_walk_summary(walks: list[Any]) -> dict[str, Any]:
    total_walks = len(walks); total_minutes = sum(walk.duration_minutes for walk in walks)
    latest = walks[0] if walks else None
    return {"total_walks": total_walks, "total_minutes": total_minutes, "average_duration_minutes": round(total_minutes / total_walks) if total_walks else 0, "latest_walk": latest, "latest_heat_risk_status": latest.heat_risk_status if latest else None, "message": "Your recent walks are based on the sessions you saved." if latest else "No completed walks yet. Start Active Walk when you are ready."}
