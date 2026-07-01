"""
tests/publishers/test_youtube.py
==================================
Unit tests for agent/publishers/youtube.py.

publish() is expected to raise NotImplementedError until the
YouTube Data API v3 integration is implemented.
"""

from __future__ import annotations

import pytest

from agent.publishers.base import ArticleSummary, ContentPackage
from agent.publishers.youtube import YouTubePublisher, _MAX_POST_CHARS


@pytest.fixture
def package() -> ContentPackage:
    return ContentPackage(
        topic="Top Tech News",
        digest="Brief digest.",
        articles=[
            ArticleSummary(
                title="Article One",
                url="https://example.com/one",
                summary="Summary of article one.",
                relevance_score=5,
                source="Example",
            ),
            ArticleSummary(
                title="Article Two",
                url="https://example.com/two",
                summary="Summary of article two.",
                relevance_score=4,
                source="Example",
            ),
        ],
        keywords=["youtube", "tech"],
        raw_post="Hey everyone! Big tech week.",
    )


class TestYouTubePublisherFormatContent:
    def test_returns_non_empty_string(self, package: ContentPackage) -> None:
        result = YouTubePublisher().format_content(package)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_raw_post(self, package: ContentPackage) -> None:
        result = YouTubePublisher().format_content(package)
        assert package.raw_post in result

    def test_includes_source_links(self, package: ContentPackage) -> None:
        result = YouTubePublisher().format_content(package)
        assert "https://example.com/one" in result

    def test_does_not_exceed_post_limit(self, package: ContentPackage) -> None:
        long_package = ContentPackage(
            topic=package.topic,
            digest=package.digest,
            articles=package.articles,
            keywords=package.keywords,
            raw_post="D" * (_MAX_POST_CHARS + 500),
        )
        result = YouTubePublisher().format_content(long_package)
        assert len(result) <= _MAX_POST_CHARS


class TestYouTubePublisherPublish:
    def test_publish_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            YouTubePublisher().publish("post content")
