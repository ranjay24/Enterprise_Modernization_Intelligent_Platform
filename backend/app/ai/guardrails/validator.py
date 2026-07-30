"""AI Guardrails — input validation, policy enforcement, and prompt injection detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a guardrails validation check."""
    passed: bool = True
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sanitized_content: str = ""

    @property
    def is_clean(self) -> bool:
        return self.passed and not self.violations


class PromptValidator:
    """Validates prompts before they are sent to foundation models.

    Checks:
    - Prompt length within model limits
    - No prompt injection patterns
    - No sensitive data leakage
    - Content policy compliance
    """

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"you\s+are\s+now\s+a",
        r"system\s*:\s*you",
        r"<\|system\|>",
        r"<\|user\|>",
        r"jailbreak",
        r"DAN\s+mode",
        r"act\s+as\s+if",
        r"pretend\s+you\s+are",
        r"disregard\s+(all|any|your)\s+(rules|instructions|guidelines)",
        r"new\s+instructions?:",
        r"override\s+(your|all)\s+(safety|rules)",
        r"\[INST\]",
        r"\[/INST\]",
        r"Human:\s*",
        r"Assistant:\s*",
    ]

    SENSITIVE_PATTERNS = [
        (r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+", "password"),
        (r"(?i)(secret|secret_key|api_key|apikey)\s*[=:]\s*\S+", "secret"),
        (r"(?i)(access_key|aws_access_key_id)\s*[=:]\s*\S+", "aws_access_key"),
        (r"(?i)(token|auth_token|bearer)\s*[=:]\s*\S+", "token"),
        (r"(?i)(private_key)\s*[=:]\s*\S+", "private_key"),
        (r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "credit_card"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
        (r"(?i)(jdbc:|mysql:|postgres:|mongodb:|redis:)://\S+", "connection_string"),
    ]

    def __init__(self, max_prompt_length: int = 30000):
        self._max_prompt_length = max_prompt_length
        self._injection_re = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]
        self._sensitive_re = [(re.compile(p), label) for p, label in self.SENSITIVE_PATTERNS]

    def validate(self, prompt: str, system_prompt: str = "") -> ValidationResult:
        """Run all validation checks on a prompt."""
        result = ValidationResult(sanitized_content=prompt)

        self._check_length(prompt, result)
        self._check_injection(prompt, result)
        self._check_sensitive(prompt, result)
        self._check_content_policy(prompt, result)

        if system_prompt:
            self._check_injection(system_prompt, result, context="system_prompt")

        return result

    def _check_length(self, prompt: str, result: ValidationResult):
        if len(prompt) > self._max_prompt_length:
            result.passed = False
            result.violations.append(
                f"Prompt length {len(prompt)} exceeds maximum {self._max_prompt_length}"
            )

    def _check_injection(self, content: str, result: ValidationResult, context: str = "prompt"):
        for pattern in self._injection_re:
            match = pattern.search(content)
            if match:
                result.passed = False
                result.violations.append(
                    f"Potential prompt injection detected in {context}: '{match.group()}'"
                )

    def _check_sensitive(self, content: str, result: ValidationResult):
        for pattern, label in self._sensitive_re:
            match = pattern.search(content)
            if match:
                redacted = content[:match.start()] + f"[REDACTED:{label}]" + content[match.end():]
                result.sanitized_content = redacted
                result.warnings.append(f"Sensitive data ({label}) detected and redacted")
                logger.warning("sensitive_data_detected", label=label)

    def _check_content_policy(self, content: str, result: ValidationResult):
        lower = content.lower()
        policy_violations = []
        if any(term in lower for term in ["hack", "exploit", "vulnerability scan"]):
            policy_violations.append("potentially harmful content")
        if policy_violations:
            result.warnings.extend(policy_violations)
