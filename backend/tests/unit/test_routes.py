"""Route contract tests — no shadowed/duplicate routes."""


class TestArtifactRoutes:
    """Artifact routes must be unique and reachable."""

    def test_no_duplicate_artifact_route_paths(self):
        from app.routes.results import router

        paths = [route.path for route in router.routes]
        assert paths.count("/results/{job_id}/artifacts/{artifact_name}") == 1
        assert paths.count("/results/{job_id}/artifacts/{artifact_name}/content") == 1

    def test_artifact_route_handlers_distinct(self):
        from app.routes.results import router

        for route in router.routes:
            if route.path == "/results/{job_id}/artifacts/{artifact_name}":
                assert route.endpoint.__name__ == "get_artifact"
