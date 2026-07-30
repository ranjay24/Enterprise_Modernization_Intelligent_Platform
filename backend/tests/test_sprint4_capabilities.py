"""Sprint 4 tests — Capabilities registry."""

import pytest


class TestCapabilityModels:
    def test_defaults(self):
        from app.capabilities.models import Capability, CapabilityCategory
        c = Capability()
        assert c.name == ""
        assert c.category == CapabilityCategory.ANALYSIS
        assert c.is_enabled is True
        assert c.requires_ai is False
        assert c.supported_models == []

    def test_to_dict(self):
        from app.capabilities.models import Capability, CapabilityCategory
        c = Capability(
            name="test_cap",
            category=CapabilityCategory.AI,
            description="Test",
            requires_ai=True,
            supported_models=["model-a"],
        )
        d = c.to_dict()
        assert d["name"] == "test_cap"
        assert d["category"] == "ai"
        assert d["requires_ai"] is True
        assert d["supported_models"] == ["model-a"]

    def test_from_dict(self):
        from app.capabilities.models import Capability
        data = {"name": "from_dict", "category": "report", "version": "2.0.0"}
        c = Capability.from_dict(data)
        assert c.name == "from_dict"
        assert c.version == "2.0.0"

    def test_invalid_category_raises(self):
        from app.capabilities.models import CapabilityCategory
        with pytest.raises(ValueError):
            CapabilityCategory("invalid_category")


class TestCapabilityRegistry:
    def test_defaults_registered(self):
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        assert len(reg.list_all()) >= 15

    def test_get(self):
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        cap = reg.get("static_analysis")
        assert cap is not None
        assert cap.name == "static_analysis"
        assert cap.version == "2.0.0"

    def test_get_nonexistent(self):
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        assert reg.get("nonexistent") is None

    def test_list_by_category(self):
        from app.capabilities.models import CapabilityCategory
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        ai_caps = reg.list_by_category(CapabilityCategory.AI)
        assert len(ai_caps) >= 5
        assert all(c.requires_ai for c in ai_caps)

    def test_get_enabled(self):
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        enabled = reg.get_enabled()
        assert len(enabled) >= 15
        assert all(c.is_enabled for c in enabled)

    def test_get_ai_capabilities(self):
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        ai = reg.get_ai_capabilities()
        assert len(ai) >= 5
        assert all(c.requires_ai for c in ai)

    def test_register_custom(self):
        from app.capabilities.models import Capability
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        initial = len(reg.list_all())
        reg.register(Capability(name="custom", description="Custom"))
        assert len(reg.list_all()) == initial + 1

    def test_to_dict(self):
        from app.capabilities.registry import CapabilityRegistry
        reg = CapabilityRegistry()
        d = reg.to_dict()
        assert "capabilities" in d
        assert "total" in d
        assert "categories" in d
        assert "ai_models" in d
        assert d["total"] >= 15
        assert "analysis" in d["categories"]
