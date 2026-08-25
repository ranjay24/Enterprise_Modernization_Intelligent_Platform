"""Spec 19 — deterministic AWS service recommendations.

Covers the mapping rules in `recommend_aws_services()` and the additive
`aws_services_map` / `aws_recommendations` keys on migration waves.
Offline-safe: no AWS, no Bedrock, no network.
"""


def _service(**overrides):
    svc = {
        "name": "TestService",
        "description": "desc",
        "cohesion_score": 80,
        "coupling_score": 20,
        "classes": ["TestService"],
        "packages": ["com.test"],
        "api_endpoints": [],
        "database_tables": [],
        "confidence": 80,
        "readiness": "green",
        "risk_level": "low",
        "business_capability": "test",
    }
    svc.update(overrides)
    return svc


def _names(recs):
    return [r["service_name"] for r in recs]


class TestRecommendAWSMapping:
    """Per-rule mapping behaviour."""

    def test_rest_only_service(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(api_endpoints=[
            {"method": "GET", "path": "/x", "handler_class": "C", "handler_method": "m"},
        ])
        names = _names(recommend_aws_services(svc))
        assert "Amazon API Gateway" in names
        assert "AWS Lambda" in names
        assert "Amazon CloudWatch" in names
        assert "Amazon RDS" not in names
        assert "Amazon DynamoDB" not in names

    def test_relational_table_name_maps_to_rds(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(database_tables=["orders", "customers", "payments"])
        names = _names(recommend_aws_services(svc))
        assert "Amazon RDS" in names
        assert "Amazon DynamoDB" not in names

    def test_non_relational_table_name_maps_to_dynamodb(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(database_tables=["audit_logs", "notifications"])
        names = _names(recommend_aws_services(svc))
        assert "Amazon DynamoDB" in names
        assert "Amazon RDS" not in names

    def test_relational_match_is_word_boundary(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(database_tables=["border", "reorder", "coordinates"])
        names = _names(recommend_aws_services(svc))
        assert "Amazon DynamoDB" in names
        assert "Amazon RDS" not in names

    def test_empty_tables_no_database_service(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service()))
        assert "Amazon RDS" not in names
        assert "Amazon DynamoDB" not in names

    def test_broker_kafka_maps_to_msk(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service(broker_role="kafka")))
        assert "Amazon MSK" in names
        assert "Amazon MQ" not in names

    def test_broker_rabbitmq_maps_to_mq(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service(broker_role="rabbitmq")))
        assert "Amazon MQ" in names
        assert "Amazon MSK" not in names

    def test_broker_both_maps_to_msk_and_mq(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service(broker_role="both")))
        assert "Amazon MSK" in names
        assert "Amazon MQ" in names

    def test_broker_none_maps_to_neither(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service(broker_role="none")))
        assert "Amazon MSK" not in names
        assert "Amazon MQ" not in names

    def test_file_class_maps_to_s3(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(classes=["FileUploader", "DocumentService"])
        names = _names(recommend_aws_services(svc))
        assert "Amazon S3" in names

    def test_no_file_class_no_s3(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service()))
        assert "Amazon S3" not in names

    def test_file_match_is_word_boundary(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(classes=["ProfileController", "Manifold"])
        names = _names(recommend_aws_services(svc))
        assert "Amazon S3" not in names

    def test_compute_fargate_when_db_backed(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service(database_tables=["orders"])))
        assert "Amazon ECS on Fargate" in names
        assert "AWS Lambda" not in names

    def test_compute_fargate_when_many_classes(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(classes=[f"Class{i}" for i in range(7)])
        names = _names(recommend_aws_services(svc))
        assert "Amazon ECS on Fargate" in names
        assert "AWS Lambda" not in names

    def test_compute_lambda_otherwise(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service()))
        assert "AWS Lambda" in names
        assert "Amazon ECS on Fargate" not in names

    def test_cloudwatch_always_present(self):
        from app.ai.orchestrator import recommend_aws_services

        names = _names(recommend_aws_services(_service()))
        assert "Amazon CloudWatch" in names

    def test_recommendation_fields_populated(self):
        from app.ai.orchestrator import recommend_aws_services

        recs = recommend_aws_services(_service(api_endpoints=[{"method": "GET", "path": "/x"}]))
        assert recs
        for rec in recs:
            assert set(rec) == {
                "service_name",
                "use_case",
                "justification",
                "alternatives",
                "pricing_model",
                "free_tier_eligible",
            }
            assert rec["pricing_model"] == "pay-as-you-go"
            assert rec["free_tier_eligible"] is True
            assert isinstance(rec["alternatives"], list)

    def test_capped_at_six_keeps_cloudwatch_and_compute(self):
        from app.ai.orchestrator import recommend_aws_services

        svc = _service(
            api_endpoints=[{"method": "GET", "path": "/x"}],
            database_tables=["orders"],
            broker_role="both",
            classes=["FileStorage", "AttachmentHandler"],
        )
        recs = recommend_aws_services(svc)
        names = _names(recs)
        assert len(recs) == 6
        assert "Amazon CloudWatch" in names
        assert "Amazon ECS on Fargate" in names


class TestMigrationWaveIntegration:
    """generate_migration_waves keeps its contract and adds AWS keys."""

    def _waves(self):
        from app.ai.orchestrator import generate_migration_waves

        boundaries = [
            _service(
                name="PaymentService",
                api_endpoints=[{"method": "POST", "path": "/pay"}],
                database_tables=["payments", "customers"],
                classes=[f"Payment{c}" for c in range(8)],
                confidence=80,
                risk_level="low",
            ),
            _service(
                name="NotificationService",
                api_endpoints=[{"method": "POST", "path": "/notify"}],
                database_tables=[],
                classes=["Notifier"],
                confidence=90,
                risk_level="low",
            ),
        ]
        return generate_migration_waves(boundaries, {}, None)

    def test_services_stays_list_of_strings(self):
        result = self._waves()
        for wave in result["waves"]:
            assert isinstance(wave["services"], list)
            assert all(isinstance(name, str) for name in wave["services"])

    def test_aws_keys_added_per_wave(self):
        result = self._waves()
        for wave in result["waves"]:
            assert "aws_services_map" in wave
            assert "aws_recommendations" in wave
            assert set(wave["aws_services_map"]) == set(wave["services"])
            for svc_name in wave["services"]:
                assert wave["aws_services_map"][svc_name]
                assert wave["aws_recommendations"][svc_name]

    def test_existing_wave_keys_preserved(self):
        wave = self._waves()["waves"][0]
        for key in (
            "wave_number",
            "name",
            "services",
            "timeline_weeks",
            "estimated_engineers",
            "dependencies",
            "risk_level",
            "migration_complexity",
            "justification",
        ):
            assert key in wave

    def test_empty_boundaries_unchanged(self):
        from app.ai.orchestrator import generate_migration_waves

        assert generate_migration_waves([], {}, None) == {
            "waves": [],
            "total_weeks": 0,
            "recommended_order": [],
        }
