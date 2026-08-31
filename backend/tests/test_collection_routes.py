from app.api.routes.dogs import router as dogs_router
from app.api.routes.walks import router as walks_router


def test_collection_routes_are_slashless_for_the_vercel_proxy():
    dog_paths = {route.path for route in dogs_router.routes}
    walk_paths = {route.path for route in walks_router.routes}

    assert "" in dog_paths
    assert "" in walk_paths
    assert "/" not in dog_paths
    assert "/" not in walk_paths
