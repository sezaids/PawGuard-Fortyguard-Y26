from app.services.heatmap_view import heatmap_view_from_activity


def test_completed_heatmap_exposes_real_geojson_and_stats():
    activity = {"message": "Completed", "data": {"activity_id": "abc", "status": "Completed", "result": {"map_data": {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"temperature": 29}, "geometry": {"type": "Polygon", "coordinates": []}}]}, "stats_data": {"Temperature_stats": {"Mean": 29}}}}}
    result = heatmap_view_from_activity(activity)
    assert result["state"] == "completed"
    assert result["map_data"] == activity["data"]["result"]["map_data"]
    assert result["stats_data"]["Temperature_stats"]["Mean"] == 29


def test_completed_heatmap_without_tiles_is_no_data():
    result = heatmap_view_from_activity({"data": {"activity_id": "abc", "status": "Completed", "result": {"map_data": {"type": "FeatureCollection", "features": []}}}})
    assert result["state"] == "no_data"


def test_pending_and_failed_heatmaps_have_clear_states():
    assert heatmap_view_from_activity({"data": {"activity_id": "abc", "status": "Processing"}})["state"] == "processing"
    assert heatmap_view_from_activity({"message": "Failed", "data": {"activity_id": "abc", "status": "Failed"}})["state"] == "failed"
