"""Centralized UUID generation."""

import uuid


def generate_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())
