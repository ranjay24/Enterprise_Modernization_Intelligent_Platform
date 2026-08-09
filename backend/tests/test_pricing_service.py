"""Tests for AWS Pricing API integration in the ai_cost stage.

Covers the real on-demand rate lookup path (with a stubbed get_products),
the graceful fallback to fixed formulas, and the footprint builder.
"""

import json

import pytest

from app.services.pricing_service import (
    AwsPricingService,
    EBS_VOLUME_TYPE,
    EC2_INSTANCE_TYPE,
    HOURS_PER_MONTH,
    MAX_EC2,
    RDS_INSTANCE_TYPE,
    REGION_LOCATIONS,
)


class _FakePricingClient:
    """Canned get_products responses keyed by service + type filter."""

    def __init__(self, rates: dict, error: Exception | None = None):
        self.rates = rates
        self.error = error
        self.calls = 0

    def get_products(self, ServiceCode=None, Filters=None, MaxResults=100, NextToken=None):
        self.calls += 1
        if self.error is not None:
            raise self.error
        filters = {f["Field"]: f["Value"] for f in Filters or []}
        key = None
        if ServiceCode == "AmazonEC2":
            key = f"AmazonEC2 {filters.get('instanceType')}"
        elif ServiceCode == "AmazonRDS":
            key = f"AmazonRDS {filters.get('instanceType')}"
        elif ServiceCode == "AmazonEBS":
            key = f"AmazonEBS {filters.get('volumeType')}"
        rate = self.rates.get(key)
        if rate is None:
            return {"PriceList": [], "NextToken": None}
        price_json = json.dumps(
            {
                "product": {},
                "terms": {
                    "OnDemand": {
                        "term1": {
                            "priceDimensions": {
                                "dim1": {"pricePerUnit": {"USD": str(rate)}}
                            }
                        }
                    }
                },
            }
        )
        return {"PriceList": [price_json], "NextToken": None}


class _FakeClients:
    def __init__(self, pricing):
        self._pricing = pricing

    @property
    def pricing(self):
        return self._pricing


def _service(rates: dict, region: str = "us-east-1", error: Exception | None = None):
    client = _FakePricingClient(rates, error=error)
    return AwsPricingService(clients=_FakeClients(client), region=region), client


def _analysis(total_lines=5000, total_classes=0):
    return {
        "metrics": {
            "total_lines": total_lines,
            "total_classes": total_classes,
            "god_classes": [],
            "circular_dependencies": [],
        }
    }


def _rates(ec2=0.0416, rds=0.034, ebs=0.08):
    return {
        f"AmazonEC2 {EC2_INSTANCE_TYPE}": ec2,
        f"AmazonRDS {RDS_INSTANCE_TYPE}": rds,
        f"AmazonEBS {EBS_VOLUME_TYPE}": ebs,
    }


class TestFootprint:
    def test_defaults_without_metrics(self):
        service, _ = _service(_rates())
        footprint = service.build_footprint({"metrics": {}}, [])
        assert footprint["ec2_instances"] == 1
        assert footprint["rds_instances"] == 1
        assert footprint["ebs_gb"] == 30

    def test_scales_with_codebase(self):
        service, _ = _service(_rates())
        footprint = service.build_footprint(_analysis(total_lines=5000, total_classes=100), [{"name": "S1"}])
        assert footprint["ec2_instances"] == 2
        assert footprint["ebs_gb"] == 50

    def test_caps_ec2_count(self):
        service, _ = _service(_rates())
        footprint = service.build_footprint(_analysis(total_classes=100000), [])
        assert footprint["ec2_instances"] == MAX_EC2


class TestRateLookup:
    def test_ec2_on_demand_hourly(self):
        service, client = _service(_rates(ec2=0.0416))
        assert service.ec2_on_demand_hourly(EC2_INSTANCE_TYPE) == 0.0416
        assert client.calls == 1

    def test_results_are_cached(self):
        service, client = _service(_rates(ec2=0.0416))
        assert service.ec2_on_demand_hourly(EC2_INSTANCE_TYPE) == 0.0416
        assert service.ec2_on_demand_hourly(EC2_INSTANCE_TYPE) == 0.0416
        assert client.calls == 1

    def test_missing_rate_returns_none(self):
        service, _ = _service({"AmazonEC2 t3.medium": 0.0416})
        assert service.ebs_monthly_gb() is None

    def test_api_error_returns_none(self):
        service, _ = _service(_rates(), error=RuntimeError("NoCredentials"))
        assert service.ec2_on_demand_hourly(EC2_INSTANCE_TYPE) is None

    def test_unknown_region_returns_none(self):
        service, _ = _service(_rates(), region="us-mars-1")
        assert service.estimate_monthly_infra(_analysis(), []) == (None, {})

    def test_known_region_locations(self):
        assert REGION_LOCATIONS["us-east-1"] == "US East (N. Virginia)"
        assert REGION_LOCATIONS["us-west-2"] == "US West (Oregon)"


class TestEstimateMonthlyInfra:
    def test_computes_total_from_real_rates(self):
        service, _ = _service(_rates(ec2=0.0416, rds=0.034, ebs=0.08))
        total, breakdown = service.estimate_monthly_infra(
            _analysis(total_lines=5000, total_classes=100),
            [{"name": "S1"}, {"name": "S2"}],
        )
        expected_compute = 2 * 0.0416 * HOURS_PER_MONTH
        expected_database = 1 * 0.034 * HOURS_PER_MONTH
        expected_storage = 50 * 0.08
        assert total == pytest.approx(
            expected_compute + expected_database + expected_storage
        )
        assert breakdown["ec2_instances"] == 2
        assert breakdown["pricing_region"] == "us-east-1"

    def test_incomplete_rates_fall_back_to_none(self):
        service, _ = _service({"AmazonEC2 t3.medium": 0.0416})
        assert service.estimate_monthly_infra(_analysis(), []) == (None, {})


class TestOrchestratorIntegration:
    def test_no_pricing_uses_formulas(self):
        from app.ai.orchestrator import generate_cost_comparison

        result = generate_cost_comparison(_analysis(total_lines=5000), [{"name": "S1"}, {"name": "S2"}])
        assert result["current_monthly"] == pytest.approx(1000)
        assert result["migration_impact"]["pricing_source"] == "estimate-formulas"

    def test_pricing_uses_real_rates(self):
        from app.ai.orchestrator import generate_cost_comparison

        service, _ = _service(_rates(ec2=0.0416, rds=0.034, ebs=0.08))
        result = generate_cost_comparison(
            _analysis(total_lines=5000, total_classes=100),
            [{"name": "S1"}, {"name": "S2"}],
            pricing=service,
        )
        assert result["migration_impact"]["pricing_source"] == "aws-pricing-api"
        expected_infra = 2 * 0.0416 * HOURS_PER_MONTH + 0.034 * HOURS_PER_MONTH + 50 * 0.08
        expected_monthly = expected_infra + 100 + 600
        assert result["current_monthly"] == pytest.approx(expected_monthly, abs=0.01)

    def test_failed_pricing_falls_back_to_formulas(self):
        from app.ai.orchestrator import generate_cost_comparison

        service, _ = _service(_rates(), region="us-mars-1")
        result = generate_cost_comparison(_analysis(total_lines=5000), [{"name": "S1"}], pricing=service)
        assert result["current_monthly"] == pytest.approx(900)
        assert result["migration_impact"]["pricing_source"] == "estimate-formulas"


class TestClientsFactory:
    def test_pricing_client_exposed(self):
        from app.aws.clients import AWSClients
        from app.core.settings import Settings

        clients = AWSClients(Settings())
        assert hasattr(clients.pricing, "get_products")
        clients.close()
