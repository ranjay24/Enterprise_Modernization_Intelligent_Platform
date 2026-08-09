"""Regression fixture test for the Java static analyzer (P7.5).

Locks known-good analyzer output against a checked-in monolith fixture so
future analyzer changes cannot silently regress class/endpoint counting.

Baseline (locked 2026-08-08, fixture = tests/fixtures/training-certificate-monolith):
  - 9 classes across 9 files
  - 5 endpoints (class-level @RequestMapping join + bare mappings)
  - 4 intra-project injection edges; no external framework imports counted
"""

import os

from app.services.static_analyzer import analyze_java_codebase

FIXTURE_ROOT = os.path.join(
    os.path.dirname(__file__),
    "..",
    "fixtures",
    "training-certificate-monolith",
)


class TestStaticAnalyzerFixture:
    def test_known_good_class_and_endpoint_counts(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))

        assert result.metrics["total_classes"] == 9
        assert result.metrics["total_endpoints"] == 5
        assert len(result.classes) == 9
        assert len(result.endpoints) == 5

    def test_known_good_class_names(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        names = {c.name for c in result.classes}
        assert names == {
            "Certificate",
            "CertificateApplication",
            "CertificateController",
            "CertificateRepository",
            "CertificateService",
            "Training",
            "TrainingController",
            "TrainingRepository",
            "TrainingService",
        }

    def test_known_good_endpoint_paths(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        endpoints = {(e.method, e.path, e.handler_class) for e in result.endpoints}
        assert endpoints == {
            ("GET", "/api/certificates", "CertificateController"),
            ("POST", "/api/certificates", "CertificateController"),
            ("GET", "/api/certificates/{id}", "CertificateController"),
            ("GET", "/api/trainings", "TrainingController"),
            ("DELETE", "/api/trainings/{id}", "TrainingController"),
        }

    def test_class_level_request_mapping_joins_handler_paths(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        paths = {e.path for e in result.endpoints}
        assert "/api/certificates/{id}" in paths
        assert "/api/trainings/{id}" in paths

    def test_bare_mapping_resolves_to_class_prefix(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        # @GetMapping/@PostMapping with no explicit path inherit the class-level
        # @RequestMapping("/api/certificates") prefix and must not be doubled.
        count = sum(1 for e in result.endpoints if e.path == "/api/certificates")
        assert count == 2
        assert not any("/api/certificates/api/certificates" in e.path for e in result.endpoints)

    def test_dependency_edges_are_intra_project_only(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        project_classes = {c.name for c in result.classes}
        assert len(result.dependency_edges) == 4
        for edge in result.dependency_edges:
            assert edge["source"] in project_classes
            assert edge["target"] in project_classes
            assert edge["type"] == "injection"

    def test_external_framework_imports_not_counted_as_dependencies(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        targets = {e["target"] for e in result.dependency_edges}
        assert not any(
            t.startswith(("java.", "jakarta.", "org.springframework"))
            for t in targets
        )

    def test_package_tree(self):
        result = analyze_java_codebase(os.path.normpath(FIXTURE_ROOT))
        assert set(result.package_tree.keys()) == {"com.training"}
        assert len(result.package_tree["com.training"]) == 9
