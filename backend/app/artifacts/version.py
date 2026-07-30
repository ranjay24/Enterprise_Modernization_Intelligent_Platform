"""Artifact versioner — generates checksums and version strings."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

PLATFORM_VERSION = "1.0.0"
ARTIFACT_VERSION = "1.0.0"


class ArtifactVersioner:
    """Handles artifact versioning and checksum generation."""

    @staticmethod
    def compute_checksum(data: dict | str) -> str:
        """Compute SHA256 checksum of artifact content."""
        if isinstance(data, dict):
            content = json.dumps(data, sort_keys=True, default=str)
        else:
            content = str(data)
        return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_artifact_id() -> str:
        """Generate a unique artifact ID."""
        import uuid
        return str(uuid.uuid4())

    @staticmethod
    def get_platform_version() -> str:
        return PLATFORM_VERSION

    @staticmethod
    def get_artifact_version() -> str:
        return ARTIFACT_VERSION

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
