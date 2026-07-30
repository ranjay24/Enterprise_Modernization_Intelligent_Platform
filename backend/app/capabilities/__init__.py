"""Capabilities package — platform feature registry."""

from app.capabilities.models import Capability, CapabilityCategory
from app.capabilities.registry import CapabilityRegistry

__all__ = ["Capability", "CapabilityCategory", "CapabilityRegistry"]
