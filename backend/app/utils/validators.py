"""General-purpose validation utilities."""

from typing import Any


def is_non_empty_string(value: Any) -> bool:
    """Check if value is a non-empty string."""
    return isinstance(value, str) and len(value.strip()) > 0


def is_valid_number(value: Any, min_val: float | None = None, max_val: float | None = None) -> bool:
    """Check if value is a valid number within optional bounds."""
    if not isinstance(value, (int, float)):
        return False
    if min_val is not None and value < min_val:
        return False
    if max_val is not None and value > max_val:
        return False
    return True
