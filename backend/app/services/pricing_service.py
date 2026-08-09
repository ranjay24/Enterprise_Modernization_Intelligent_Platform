"""AWS Pricing API integration for the ai_cost stage.

Replaces hardcoded per-unit infrastructure formulas with real AWS on-demand
rates when credentials are available (i.e. in the Lambda worker). Every lookup
degrades gracefully to ``None`` on any failure (missing credentials, network
errors, unknown instance type, empty results), so callers always fall back to
the deterministic formulas in ``app.ai.orchestrator``.

The static analyzer does not report real instance types, so the footprint is
derived from scan metrics (classes, LOC, service boundaries) and priced with
default on-demand instance types (t3.medium, db.t3.small, gp3 storage).
"""

from __future__ import annotations

import json
import time
from math import ceil

import structlog

logger = structlog.get_logger(__name__)

HOURS_PER_MONTH = 730

# Pricing API location names for common regions. The Pricing API filters on
# these exact display names; unknown regions simply fail the lookup and the
# caller falls back to formulas.
REGION_LOCATIONS = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "ca-central-1": "Canada (Central)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-west-3": "EU (Paris)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-north-1": "EU (Stockholm)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "sa-east-1": "South America (São Paulo)",
}

# Default instance types used to price the assumed footprint (the static
# analyzer reports no real infrastructure inventory).
EC2_INSTANCE_TYPE = "t3.medium"
RDS_INSTANCE_TYPE = "db.t3.small"
EBS_VOLUME_TYPE = "General Purpose"

# Assumption knobs: resources per unit of codebase size.
CLASSES_PER_EC2 = 50
GB_PER_KILOLINE = 10
MIN_EBS_GB = 30
MAX_EC2 = 16

DEFAULT_CACHE_TTL = 86400


class _RateCache:
    """Small TTL cache keyed by (service, sorted filters)."""

    def __init__(self, ttl: int = DEFAULT_CACHE_TTL):
        self._ttl = ttl
        self._data: dict[tuple, tuple[float, float]] = {}

    def get(self, key: tuple) -> float | None:
        item = self._data.get(key)
        if item is None:
            return None
        expires, value = item
        if time.monotonic() > expires:
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: tuple, value: float) -> None:
        self._data[key] = (time.monotonic() + self._ttl, value)


class AwsPricingService:
    """Fetches real on-demand unit rates from the AWS Pricing API.

    All network calls are guarded: any failure returns ``None`` so callers can
    always fall back to the deterministic cost formulas.
    """

    def __init__(
        self,
        clients=None,
        region: str = "us-east-1",
        cache_ttl: int = DEFAULT_CACHE_TTL,
    ):
        self._clients = clients
        self._region = region
        self._cache = _RateCache(cache_ttl)

    def clear_cache(self) -> None:
        self._cache = _RateCache()

    def _client(self):
        if self._clients is None:
            from app.core.dependencies import get_aws_clients

            self._clients = get_aws_clients()
        return self._clients.pricing

    def _location(self) -> str | None:
        return REGION_LOCATIONS.get(self._region)

    def get_products(self, service_code: str, filters: list[dict]) -> list[str]:
        """Paginated ``get_products`` returning raw price list JSON strings."""
        client = self._client()
        products: list[str] = []
        token = None
        while True:
            kwargs = {
                "ServiceCode": service_code,
                "Filters": filters,
                "MaxResults": 100,
            }
            if token:
                kwargs["NextToken"] = token
            response = client.get_products(**kwargs)
            products.extend(response.get("PriceList", []))
            token = response.get("NextToken")
            if not token:
                break
        return products

    def _on_demand_usd(self, service_code: str, filters: list[dict]) -> float | None:
        """Return the first on-demand USD unit price matching the filters."""
        key = (service_code, tuple(sorted((f["Field"], f["Value"]) for f in filters)))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            for raw in self.get_products(service_code, filters):
                try:
                    product = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                terms = product.get("terms", {}).get("OnDemand", {})
                for _term_key, term in terms.items():
                    for _dim_key, dim in term.get("priceDimensions", {}).items():
                        rate = dim.get("pricePerUnit", {}).get("USD")
                        if rate:
                            value = float(rate)
                            self._cache.set(key, value)
                            return value
        except Exception as exc:
            logger.warning(
                "pricing_api_lookup_failed",
                service=service_code,
                error=str(exc),
            )
        return None

    def ec2_on_demand_hourly(self, instance_type: str) -> float | None:
        location = self._location()
        if not location:
            return None
        return self._on_demand_usd(
            "AmazonEC2",
            [
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            ],
        )

    def rds_on_demand_hourly(
        self,
        instance_type: str,
        engine: str = "MySQL",
    ) -> float | None:
        location = self._location()
        if not location:
            return None
        return self._on_demand_usd(
            "AmazonRDS",
            [
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": engine},
                {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Single-AZ"},
            ],
        )

    def ebs_monthly_gb(self, volume_type: str = EBS_VOLUME_TYPE) -> float | None:
        location = self._location()
        if not location:
            return None
        return self._on_demand_usd(
            "AmazonEBS",
            [
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
                {"Type": "TERM_MATCH", "Field": "volumeType", "Value": volume_type},
                {"Type": "TERM_MATCH", "Field": "location", "Value": location},
            ],
        )

    def build_footprint(self, analysis_data: dict, boundaries: list[dict]) -> dict:
        """Assumed infrastructure footprint derived from scan metrics.

        The static analyzer reports code metrics only, so instance counts are
        estimated: ~1 t3.medium per 50 classes (capped), 10 GB gp3 storage per
        1000 LOC (floored), and one db.t3.small for the service fleet.
        """
        metrics = analysis_data.get("metrics", {})
        total_classes = metrics.get("total_classes", 0)
        total_loc = metrics.get("total_lines", 0)
        num_services = max(1, len(boundaries))

        if total_classes > 0:
            ec2 = min(MAX_EC2, ceil(total_classes / CLASSES_PER_EC2))
        else:
            ec2 = 1
        ebs_gb = max(MIN_EBS_GB, ceil(total_loc / 1000) * GB_PER_KILOLINE)
        rds = 1 if num_services >= 1 else 0
        return {
            "ec2_instances": ec2,
            "rds_instances": rds,
            "ebs_gb": ebs_gb,
        }

    def estimate_monthly_infra(
        self,
        analysis_data: dict,
        boundaries: list[dict],
    ) -> tuple[float | None, dict]:
        """Monthly infrastructure cost from real on-demand rates.

        Returns ``(total, breakdown)`` or ``(None, {})`` when any rate cannot be
        resolved (offline, unconfigured, unknown region, API error).
        """
        footprint = self.build_footprint(analysis_data, boundaries)
        if not self._location():
            logger.info("pricing_api_region_unknown", region=self._region)
            return None, {}

        ec2_hourly = self.ec2_on_demand_hourly(EC2_INSTANCE_TYPE)
        rds_hourly = self.rds_on_demand_hourly(RDS_INSTANCE_TYPE)
        ebs_gb_month = self.ebs_monthly_gb(EBS_VOLUME_TYPE)
        if ec2_hourly is None or rds_hourly is None or ebs_gb_month is None:
            logger.info(
                "pricing_api_incomplete",
                ec2_hourly=ec2_hourly,
                rds_hourly=rds_hourly,
                ebs_gb_month=ebs_gb_month,
            )
            return None, {}

        compute = footprint["ec2_instances"] * ec2_hourly * HOURS_PER_MONTH
        database = footprint["rds_instances"] * rds_hourly * HOURS_PER_MONTH
        storage = footprint["ebs_gb"] * ebs_gb_month
        total = compute + database + storage

        breakdown = {
            "compute": round(compute, 2),
            "storage": round(storage, 2),
            "database": round(database, 2),
            "ec2_instances": footprint["ec2_instances"],
            "rds_instances": footprint["rds_instances"],
            "ebs_gb": footprint["ebs_gb"],
            "ec2_rate_hourly": ec2_hourly,
            "rds_rate_hourly": rds_hourly,
            "ebs_gb_rate": ebs_gb_month,
            "pricing_region": self._region,
        }
        return total, breakdown
