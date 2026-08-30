"""Safe adapter for completed FortyGuard GeoJSON heatmap activities."""
from __future__ import annotations

from typing import Any


def heatmap_view_from_activity(activity: dict[str, Any]) -> dict[str, Any]:
    """Return only documented completed heatmap outputs; never manufacture tile data."""
    data = activity.get("data") or {}
    activity_id = data.get("activity_id")
    state = data.get("status")
    if state == "Failed":
        return {"state": "failed", "activity_id": activity_id, "message": activity.get("message") or "FortyGuard could not generate this heatmap.", "map_data": None, "stats_data": None}
    if state != "Completed":
        return {"state": "processing", "activity_id": activity_id, "message": activity.get("message") or "FortyGuard is generating the heatmap.", "map_data": None, "stats_data": None}

    result = data.get("result") or {}
    map_data = result.get("map_data")
    stats_data = result.get("stats_data")
    if not isinstance(map_data, dict) or map_data.get("type") != "FeatureCollection" or not isinstance(map_data.get("features"), list) or not map_data["features"]:
        return {"state": "no_data", "activity_id": activity_id, "message": "FortyGuard completed the request but returned no map tiles for this area.", "map_data": None, "stats_data": stats_data if isinstance(stats_data, dict) else None}
    return {"state": "completed", "activity_id": activity_id, "message": activity.get("message") or "FortyGuard heatmap is ready.", "map_data": map_data, "stats_data": stats_data if isinstance(stats_data, dict) else None}
