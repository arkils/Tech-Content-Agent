"""
tests/publishers/test_instagram.py
=====================================
Unit tests for agent/publishers/instagram.py.

publish() is expected to raise NotImplementedError until the
Meta Graph API integration is implemented.
"""

from __future__ import annotations

import pytest

from agent.publishers.base import ArticleSummary, ContentPackage
from agent.publishers.instagram import InstagramPublisher, _MAX_CAPTION_CHARS


@pytest.fixture
def package() -> ContentPackage:
    return ContentPackage(
        topic="Top Tech News",
        digest="Brief digest.",
        articles=[
            ArticleSummary(
                title="Big Announcement",
                url="https://example.com/big",
                summary="Something happened.",
                relevance_score=4,
                source="Example",
            ),
        ],
        keywords=["tech", "ai", "cloud", "python", "aws"],
        raw_post="Exciting tech news this week!",
    )


class TestInstagramPublisherFormatContent:
    def test_returns_non_empty_string(self, package: ContentPackage) -> None:
        result = InstagramPublisher().format_content(package)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_raw_post(self, package: ContentPackage) -> None:
        result = InstagramPublisher().format_content(package)
        assert package.raw_post in result

    def test_includes_hashtags(self, package: ContentPackage) -> None:
        result = InstagramPublisher().format_content(package)
        assert "#tech" in result

    def test_does_not_exceed_caption_limit(self, package: ContentPackage) -> None:
        long_package = ContentPackage(
            topic=package.topic,
            digest=package.digest,
            articles=package.articles,
            keywords=package.keywords,
            raw_post="C" * (_MAX_CAPTION_CHARS + 500),
        )
        result = InstagramPublisher().format_content(long_package)
        assert len(result) <= _MAX_CAPTION_CHARS


class TestInstagramPublisherPublish:
    def test_publish_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            InstagramPublisher().publish("caption")
