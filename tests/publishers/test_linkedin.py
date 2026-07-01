"""
tests/publishers/test_linkedin.py
===================================
Unit tests for agent/publishers/linkedin.py.

Credentials are never used in tests — publish() is expected to raise
NotImplementedError until the LinkedIn API integration is implemented.
"""

from __future__ import annotations

import pytest

from agent.publishers.base import ArticleSummary, ContentPackage
from agent.publishers.linkedin import LinkedInPublisher, _MAX_CHARS


@pytest.fixture
def package() -> ContentPackage:
    return ContentPackage(
        topic="Top Tech News",
        digest="Brief digest of this week's tech news.",
        articles=[
            ArticleSummary(
                title="Something Big Happened",
                url="https://techcrunch.com/something-big",
                summary="A major announcement was made.",
                relevance_score=5,
                source="TechCrunch",
            ),
        ],
        keywords=["aws", "ai", "cloud", "python", "devops"],
        raw_post="This week in tech: exciting things happened across AI, cloud, and open-source.",
    )


class TestLinkedInPublisherFormatContent:
    def test_returns_non_empty_string(self, package: ContentPackage) -> None:
        result = LinkedInPublisher().format_content(package)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_raw_post(self, package: ContentPackage) -> None:
        result = LinkedInPublisher().format_content(package)
        assert package.raw_post in result

    def test_includes_hashtags(self, package: ContentPackage) -> None:
        result = LinkedInPublisher().format_content(package)
        assert "#aws" in result

    def test_does_not_exceed_max_chars(self, package: ContentPackage) -> None:
        # Make a very long raw_post to trigger truncation
        long_package = ContentPackage(
            topic=package.topic,
            digest=package.digest,
            articles=package.articles,
            keywords=package.keywords,
            raw_post="A" * (_MAX_CHARS + 500),
        )
        result = LinkedInPublisher().format_content(long_package)
        assert len(result) <= _MAX_CHARS

    def test_truncated_post_ends_with_ellipsis(self, package: ContentPackage) -> None:
        long_package = ContentPackage(
            topic=package.topic,
            digest=package.digest,
            articles=package.articles,
            keywords=package.keywords,
            raw_post="B" * (_MAX_CHARS + 500),
        )
        result = LinkedInPublisher().format_content(long_package)
        assert result.endswith("...")


class TestLinkedInPublisherPublish:
    def test_publish_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            LinkedInPublisher().publish("some content")
