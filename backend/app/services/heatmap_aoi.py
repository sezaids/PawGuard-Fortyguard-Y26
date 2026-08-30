"""Small, reusable GeoJSON areas for provider heatmap requests."""


def heatmap_aoi(latitude: float, longitude: float, delta: float = 0.006) -> dict:
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[longitude - delta, latitude - delta], [longitude + delta, latitude - delta], [longitude + delta, latitude + delta], [longitude - delta, latitude + delta], [longitude - delta, latitude - delta]]]}}]}
