"""AI Response Validator — validates every AI response before returning to callers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import structlog

from app.core.analysis_profile import get_profile_for_settings

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool = True
    parsed_data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    fields_present: list[str] = field(default_factory=list)
    fields_missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence_score": self.confidence_score,
            "fields_present": self.fields_present,
            "fields_missing": self.fields_missing,
        }


class AIResponseValidator:
    """Validates AI responses for correctness, completeness, and safety.

    Checks:
    1. JSON validity
    2. Required fields present
    3. Confidence thresholds
    4. Hallucination prevention (referenced entities exist in context)
    5. Fallback handling
    """

    def __init__(self):
        self._profile = None

    def _get_profile(self):
        if self._profile is None:
            self._profile = get_profile_for_settings()
        return self._profile

    def validate(
        self,
        response_text: str,
        response_type: str = "generic",
        expected_fields: list[str] | None = None,
        known_entities: list[str] | None = None,
    ) -> ValidationResult:
        """Validate an AI response."""
        result = ValidationResult()

        if not response_text or not response_text.strip():
            result.is_valid = False
            result.errors.append("Empty response")
            return result

        parsed = self._extract_json(response_text)
        if parsed is None:
            result.is_valid = False
            result.errors.append("Response is not valid JSON")
            result.parsed_data = {"raw_response": response_text[:500]}
            return result

        result.parsed_data = parsed

        if expected_fields:
            self._check_fields(parsed, expected_fields, result)

        self._check_confidence(parsed, result)

        if known_entities:
            self._check_hallucination(parsed, known_entities, result)

        self._check_response_quality(parsed, response_type, result)

        return result

    def validate_or_fallback(
        self,
        response_text: str,
        fallback_data: dict,
        response_type: str = "generic",
        expected_fields: list[str] | None = None,
    ) -> ValidationResult:
        """Validate with automatic fallback to deterministic data."""
        result = self.validate(response_text, response_type, expected_fields)

        if not result.is_valid:
            logger.warning("response_validation_failed_using_fallback", response_type=response_type)
            result.parsed_data = fallback_data
            result.is_valid = True
            result.warnings.append("Used fallback data due to validation failure")
            result.errors.clear()

        return result

    def _extract_json(self, text: str) -> dict | None:
        """Extract JSON from response, handling markdown code blocks."""
        cleaned = text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            cleaned = "\n".join(json_lines)

        json_match = re.search(r"\{[\s\S]*\}", cleaned)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return None

    def _check_fields(self, data: dict, expected: list[str], result: ValidationResult):
        """Check required fields are present."""
        for field_name in expected:
            if field_name in data:
                result.fields_present.append(field_name)
            else:
                result.fields_missing.append(field_name)
                result.errors.append(f"Missing required field: {field_name}")

        if result.fields_missing:
            result.is_valid = False

    def _check_confidence(self, data: dict, result: ValidationResult):
        """Check confidence values exist and are reasonable."""
        min_conf = self._get_profile().min_confidence
        confidence = data.get("confidence")
        if confidence is not None:
            result.confidence_score = float(confidence)
            if result.confidence_score < min_conf:
                result.warnings.append(
                    f"Low confidence: {result.confidence_score} (minimum: {min_conf})"
                )

        for key in ("recommendations", "adrs", "waves", "findings"):
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    if isinstance(item, dict) and "confidence" in item:
                        if float(item["confidence"]) < min_conf:
                            result.warnings.append(
                                f"Low confidence in {key}: {item.get('title', item.get('name', 'unknown'))}"
                            )

    def _check_hallucination(self, data: dict, known_entities: list[str], result: ValidationResult):
        """Check that referenced entities exist in the known set."""
        known_set = set(known_entities)
        entity_fields = ["classes", "source_classes", "affected_components", "services"]

        for field_name in entity_fields:
            self._scan_for_unknowns(data, field_name, known_set, result)

    def _scan_for_unknowns(self, data: dict, field_name: str, known: set, result: ValidationResult):
        """Recursively scan for unknown entity references."""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == field_name and isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and item not in known and len(item) > 3:
                            result.warnings.append(f"Referenced entity not in analysis: {item}")
                elif isinstance(value, (dict, list)):
                    self._scan_for_unknowns(value, field_name, known, result)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._scan_for_unknowns(item, field_name, known, result)

    def _check_response_quality(self, data: dict, response_type: str, result: ValidationResult):
        """Check response quality metrics."""
        data_str = json.dumps(data)
        if len(data_str) < self._get_profile().min_response_length:
            result.warnings.append("Response appears very short")

        if response_type == "json_list":
            for key in ("recommendations", "adrs", "waves"):
                if key in data and not isinstance(data[key], list):
                    result.errors.append(f"Expected '{key}' to be a list")
                    result.is_valid = False
