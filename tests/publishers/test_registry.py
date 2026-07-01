"""
tests/publishers/test_registry.py
===================================
Tests for the publisher registry and factory in agent/publishers/__init__.py.
"""

from __future__ import annotations

import pytest

from agent.publishers import PUBLISHER_REGISTRY, get_active_publishers
from agent.publishers.base import BasePublisher


class TestPublisherRegistry:
    """Verify the registry is complete and returns correct types."""

    def test_all_expected_platforms_registered(self) -> None:
        for platform in ("blog", "linkedin", "instagram", "youtube"):
            assert platform in PUBLISHER_REGISTRY, f"{platform!r} missing from PUBLISHER_REGISTRY"

    def test_all_registry_values_are_base_publisher_subclasses(self) -> None:
        for key, cls in PUBLISHER_REGISTRY.items():
            assert issubclass(cls, BasePublisher), f"{key!r} value is not a BasePublisher subclass"

    def test_all_registry_classes_have_platform_name(self) -> None:
        for key, cls in PUBLISHER_REGISTRY.items():
            instance = cls() if key == "blog" else None
            assert cls.platform_name != "unknown", f"{key!r} publisher has default platform_name"


class TestGetActivePublishers:
    """Tests for the get_active_publishers factory function."""

    def test_returns_blog_publisher(self) -> None:
        from agent.publishers.blog import BlogPublisher

        publishers = get_active_publishers(["blog"])
        assert len(publishers) == 1
        assert isinstance(publishers[0], BlogPublisher)

    def test_returns_multiple_publishers_in_order(self) -> None:
        from agent.publishers.blog import BlogPublisher
        from agent.publishers.linkedin import LinkedInPublisher

        publishers = get_active_publishers(["blog", "linkedin"])
        assert len(publishers) == 2
        assert isinstance(publishers[0], BlogPublisher)
        assert isinstance(publishers[1], LinkedInPublisher)

    def test_empty_list_returns_empty(self) -> None:
        publishers = get_active_publishers([])
        assert publishers == []

    def test_unknown_platform_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown publisher"):
            get_active_publishers(["tiktok"])

    def test_multiple_unknown_platforms_listed_in_error(self) -> None:
        with pytest.raises(ValueError, match="tiktok"):
            get_active_publishers(["tiktok", "myspace"])
