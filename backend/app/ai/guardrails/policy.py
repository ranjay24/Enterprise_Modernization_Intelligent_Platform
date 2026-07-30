"""AI Guardrails Policy — defines acceptable use policies for AI interactions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AIPolicyRule:
    """A single AI usage policy rule."""
    rule_id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"
    severity: str = "medium"
    enabled: bool = True
    check_fn: str | None = None

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "enabled": self.enabled,
        }


@dataclass
class PolicyViolation:
    """A policy violation detected during validation."""
    rule_id: str = ""
    rule_name: str = ""
    severity: str = ""
    details: str = ""
    blocked: bool = False

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "details": self.details,
            "blocked": self.blocked,
        }


class AIPolicy:
    """Enforces AI usage policies.

    Defines what content can be sent to and received from foundation models.
    """

    def __init__(self):
        self._rules: list[AIPolicyRule] = self._default_rules()

    @staticmethod
    def _default_rules() -> list[AIPolicyRule]:
        return [
            AIPolicyRule(
                rule_id="POL-001",
                name="No Secrets in Prompts",
                description="Prompts must not contain AWS keys, passwords, tokens, or other secrets",
                category="security",
                severity="critical",
            ),
            AIPolicyRule(
                rule_id="POL-002",
                name="No Source Code in Prompts",
                description="Full source code files should not be embedded in prompts unless explicitly required",
                category="security",
                severity="high",
            ),
            AIPolicyRule(
                rule_id="POL-003",
                name="Prompt Length Limit",
                description="Prompts must not exceed the configured maximum token budget",
                category="performance",
                severity="medium",
            ),
            AIPolicyRule(
                rule_id="POL-004",
                name="Response JSON Validation",
                description="AI responses expected as JSON must be parseable",
                category="quality",
                severity="high",
            ),
            AIPolicyRule(
                rule_id="POL-005",
                name="Confidence Threshold",
                description="Recommendations below minimum confidence must be flagged",
                category="quality",
                severity="medium",
            ),
            AIPolicyRule(
                rule_id="POL-006",
                name="No Prompt Injection",
                description="Prompts must not contain injection attempts",
                category="security",
                severity="critical",
            ),
        ]

    def evaluate(self, prompt: str = "", response: str = "", context: dict = None) -> list[PolicyViolation]:
        """Evaluate content against all active policies."""
        violations = []
        ctx = context or {}

        _max_tokens_default = 7000
        try:
            from app.core.analysis_profile import get_active_profile
            from app.core.settings import get_settings
            _s = get_settings()
            _max_tokens_default = get_active_profile(_s.analysis_mode,
                                                      _s.bedrock_max_tokens,
                                                      _s.ai_prompt_max_tokens).prompt_max_tokens
        except Exception:
            pass

        for rule in self._rules:
            if not rule.enabled:
                continue

            if rule.rule_id == "POL-001" and prompt:
                if self._check_secrets(prompt):
                    violations.append(PolicyViolation(
                        rule_id=rule.rule_id, rule_name=rule.name,
                        severity=rule.severity, details="Secrets detected in prompt", blocked=True,
                    ))

            elif rule.rule_id == "POL-003" and prompt:
                max_tokens = ctx.get("max_prompt_tokens", _max_tokens_default)
                if len(prompt) > max_tokens * 4:
                    violations.append(PolicyViolation(
                        rule_id=rule.rule_id, rule_name=rule.name,
                        severity=rule.severity,
                        details=f"Prompt length {len(prompt)} chars exceeds ~{max_tokens} token budget",
                        blocked=False,
                    ))

            elif rule.rule_id == "POL-004" and response:
                if ctx.get("expect_json") and not self._is_valid_json(response):
                    violations.append(PolicyViolation(
                        rule_id=rule.rule_id, rule_name=rule.name,
                        severity=rule.severity, details="Response is not valid JSON", blocked=False,
                    ))

            elif rule.rule_id == "POL-005" and response:
                min_confidence = ctx.get("min_confidence", 0.3)

        return violations

    def register_rule(self, rule: AIPolicyRule):
        """Register a new policy rule."""
        self._rules.append(rule)

    def get_rules(self) -> list[AIPolicyRule]:
        return list(self._rules)

    @staticmethod
    def _check_secrets(content: str) -> bool:
        import re
        patterns = [
            r"AKIA[0-9A-Z]{16}",
            r"(?i)(password|secret|api_key|token)\s*[=:]\s*['\"][^'\"]{8,}",
        ]
        return any(re.search(p, content) for p in patterns)

    @staticmethod
    def _is_valid_json(text: str) -> bool:
        import json
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, TypeError):
            return False
