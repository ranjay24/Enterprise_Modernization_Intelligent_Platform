"""AI Guardrails Redaction — sensitive data masking and prompt sanitization."""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)


class PromptRedactor:
    """Masks sensitive data in prompts before sending to foundation models.

    Supports:
    - AWS credentials redaction
    - Password/secret redaction
    - Connection string redaction
    - PII redaction (SSN, credit cards)
    - Custom pattern redaction
    """

    def __init__(self):
        self._custom_patterns: list[tuple[re.Pattern, str]] = []
        self._builtin_patterns: list[tuple[re.Pattern, str, str]] = [
            (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS_ACCESS_KEY", "AWS access key"),
            (re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?"),
             "PASSWORD", "password"),
            (re.compile(r"(?i)(secret|secret_key|api_key|apikey)\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?")
             , "SECRET", "secret/API key"),
            (re.compile(r"(?i)(access_key|aws_access_key_id)\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?")
             , "AWS_KEY", "AWS access key ID"),
            (re.compile(r"(?i)(token|auth_token|bearer)\s*[=:]\s*['\"]?([^\s'\"]+)['\"]?")
             , "TOKEN", "auth token"),
            (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "CREDIT_CARD", "credit card number"),
            (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN", "social security number"),
            (re.compile(r"(?i)(jdbc|mysql|postgres|mongodb|redis)://[^\s]+"), "CONN_STRING", "database connection string"),
            (re.compile(r"(?i)arn:aws:[^\s]+"), "AWS_ARN", "AWS ARN"),
            (re.compile(r"[a-zA-Z0-9+/]{40}"), "POSSIBLE_KEY", "possible credential"),
        ]

    def redact(self, content: str) -> str:
        """Redact all sensitive patterns from content."""
        result = content

        for pattern, label, _ in self._builtin_patterns:
            result = pattern.sub(f"[REDACTED:{label}]", result)

        for pattern, label in self._custom_patterns:
            result = pattern.sub(f"[REDACTED:{label}]", result)

        return result

    def add_custom_pattern(self, pattern: str, label: str):
        """Add a custom redaction pattern."""
        self._custom_patterns.append((re.compile(pattern, re.IGNORECASE), label))

    def scan(self, content: str) -> list[dict]:
        """Scan content for sensitive data without modifying it.

        Returns list of detected sensitive items.
        """
        findings = []

        for pattern, label, description in self._builtin_patterns:
            for match in pattern.finditer(content):
                findings.append({
                    "type": label,
                    "description": description,
                    "position": match.start(),
                    "length": match.end() - match.start(),
                    "preview": (content[max(0, match.start()):match.start()+8] + "...") if len(match.group()) > 8 else match.group(),
                })

        return findings

    def sanitize_for_logging(self, content: str) -> str:
        """Sanitize content for safe logging — more aggressive than redact."""
        result = self.redact(content)
        result = re.sub(r"\b[\w.-]+@[\w.-]+\.\w+\b", "[REDACTED:EMAIL]", result)
        result = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[REDACTED:IP]", result)
        return result
