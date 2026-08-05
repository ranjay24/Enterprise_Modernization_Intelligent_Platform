"""Orphan class detection — identifies classes that do not belong to a single domain."""

from __future__ import annotations
from dataclasses import dataclass
import structlog

logger = structlog.get_logger(__name__)

ORPHAN_NAME_PATTERNS = {
    "utility": ["Utils", "Utility", "Helper", "Helpers", "Common"],
    "dto": ["DTO", "Dto", "Request", "Response", "Payload", "Login"],
    "mapper": ["Mapper", "Converter", "Transformer"],
    "validator": ["Validator", "Validation"],
    "config": ["Config", "Configuration", "Properties", "Application"],
    "exception": ["Exception", "Error", "Exceptions"],
    "support": ["Logic", "Base", "Abstract"],
}


@dataclass
class OrphanClass:
    name: str
    orphan_type: str
    used_by: list[str]
    reason: str


def _orphan_type(name: str, cls: dict) -> str:
    for otype, patterns in ORPHAN_NAME_PATTERNS.items():
        for pat in patterns:
            if pat in name:
                return otype
    return "shared_utility"


def _domains_using(cn: str, services: list[dict]) -> list[str]:
    using = []
    for s in services:
        if cn in (s.get("classes", []) or []):
            using.append(s.get("name", ""))
    return using


def detect_orphan_classes(
    services: list[dict], class_by_name: dict
) -> tuple[list[OrphanClass], list[dict]]:
    """Detect orphan classes and return (orphans, updated_services)."""
    orphans: list[OrphanClass] = []
    for svc in services:
        to_remove = []
        for cn in list(svc.get("classes", []) or []):
            cls = class_by_name.get(cn, {})
            # Never treat entity/controller/service/repo as orphan
            if (
                cls.get("is_entity")
                or cls.get("is_controller")
                or cls.get("is_service")
                or cls.get("is_repository")
                or cn.endswith("Repository")
                or cn.endswith("Controller")
                or cn.endswith("Services")
                or cn.endswith("Service")
            ):
                continue

            matched_type = None
            for otype, patterns in ORPHAN_NAME_PATTERNS.items():
                for pat in patterns:
                    if pat in cn:
                        matched_type = otype
                        break
                if matched_type:
                    break

            if matched_type in ("utility", "support", "config", "exception"):
                domains = _domains_using(cn, services)
                orphans.append(
                    OrphanClass(
                        name=cn,
                        orphan_type=matched_type,
                        used_by=domains,
                        reason=f"Infrastructure {matched_type} class shared across domains",
                    )
                )
                to_remove.append(cn)

        for cn in to_remove:
            svc["classes"].remove(cn)

    return orphans, services
