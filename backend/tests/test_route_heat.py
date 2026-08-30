from app.services.route_heat import add_relative_heat_exposure, rank_routes


def routes():
    return [
        {"id": "cool", "distance_meters": 1100, "duration_seconds": 900, "geometry": {"type": "LineString", "coordinates": [[0.1, 0.1], [0.2, 0.2]]}},
        {"id": "hot", "distance_meters": 1000, "duration_seconds": 850, "geometry": {"type": "LineString", "coordinates": [[1.1, 1.1], [1.2, 1.2]]}},
    ]


def tiles():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"temperature": 20}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [.5, 0], [.5, .5], [0, .5], [0, 0]]]}},
        {"type": "Feature", "properties": {"temperature": 35}, "geometry": {"type": "Polygon", "coordinates": [[[1, 1], [1.5, 1], [1.5, 1.5], [1, 1.5], [1, 1]]]}},
    ]}


def test_real_tile_values_produce_relative_route_exposure():
    result = add_relative_heat_exposure(routes(), tiles())
    assert result[0]["relative_heat_exposure"] == 0
    assert result[1]["relative_heat_exposure"] == 100


def test_cool_reasonable_detour_can_rank_before_hot_shortest_route():
    ranked = rank_routes(add_relative_heat_exposure(routes(), tiles()), heat_available=True)
    assert ranked[0]["id"] == "cool"
    assert ranked[0]["heat_optimized"] is True


def test_no_tile_values_falls_back_to_normal_walking_time():
    map_data = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"tile": "unknown"}, "geometry": {"type": "Polygon", "coordinates": []}}]}
    ranked = rank_routes(add_relative_heat_exposure(routes(), map_data), heat_available=False)
    assert ranked[0]["id"] == "hot"
    assert ranked[0]["relative_heat_exposure"] is None


def test_fortyguard_average_temperature_tiles_are_usable():
    heatmap = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"average_temperature": 21.5},
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [.5, 0], [.5, .5], [0, .5], [0, 0]]]},
        }],
    }
    result = add_relative_heat_exposure([routes()[0]], heatmap)
    assert result[0]["relative_heat_exposure"] == 50
