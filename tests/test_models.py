"""
tests/test_models.py
====================
Unit tests for agent/models/__init__.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agent.models import Article, ArticleSummary, ContentPackage, FeedSource, PublishResult


class TestFeedSource:
    def test_defaults(self) -> None:
        fs = FeedSource(feed_url="https://example.com/feed")
        assert fs.name == ""
        assert fs.category == "general"
        assert fs.enabled is True

    def test_from_url(self) -> None:
        fs = FeedSource.from_url("https://example.com/feed")
        assert fs.feed_url == "https://example.com/feed"
        assert fs.enabled is True

    def test_disabled_feed(self) -> None:
        fs = FeedSource(feed_url="https://example.com/feed", enabled=False)
        assert fs.enabled is False


class TestArticle:
    def test_required_fields(self) -> None:
        a = Article(url="https://example.com/article", title="Test Article")
        assert a.url == "https://example.com/article"
        assert a.title == "Test Article"

    def test_defaults(self) -> None:
        a = Article(url="https://example.com/article", title="Test Article")
        assert a.source == ""
        assert a.published_at is None
        assert a.content == ""

    def test_with_all_fields(self) -> None:
        pub = datetime(2026, 7, 2, 9, 0, tzinfo=timezone.utc)
        a = Article(
            url="https://example.com/article",
            title="Test Article",
            source="Ars Technica",
            published_at=pub,
            content="Article body text.",
        )
        assert a.source == "Ars Technica"
        assert a.published_at == pub
        assert a.content == "Article body text."


class TestArticleSummary:
    def test_required_fields(self) -> None:
        s = ArticleSummary(
            title="AI Breakthrough",
            url="https://example.com/ai",
            summary="Short summary.",
            relevance_score=4,
        )
        assert s.title == "AI Breakthrough"
        assert s.relevance_score == 4

    def test_source_default(self) -> None:
        s = ArticleSummary(title="T", url="https://x.com", summary="S", relevance_score=3)
        assert s.source == ""


class TestContentPackage:
    def test_required_fields(self) -> None:
        cp = ContentPackage(topic="AI Week", digest="Big week in AI.")
        assert cp.topic == "AI Week"
        assert cp.digest == "Big week in AI."

    def test_defaults(self) -> None:
        cp = ContentPackage(topic="AI Week", digest="Big week in AI.")
        assert cp.articles == []
        assert cp.keywords == []
        assert cp.raw_post == ""

    def test_with_articles(self) -> None:
        summary = ArticleSummary(title="T", url="https://x.com", summary="S", relevance_score=5)
        cp = ContentPackage(
            topic="AI Week",
            digest="Big week in AI.",
            articles=[summary],
            keywords=["AI", "LLM"],
        )
        assert len(cp.articles) == 1
        assert cp.keywords == ["AI", "LLM"]

    def test_articles_lists_are_independent(self) -> None:
        cp1 = ContentPackage(topic="A", digest="D")
        cp2 = ContentPackage(topic="B", digest="D")
        cp1.articles.append(
            ArticleSummary(title="T", url="https://x.com", summary="S", relevance_score=1)
        )
        assert cp2.articles == []


class TestPublishResult:
    def test_success(self) -> None:
        r = PublishResult(platform="blog", success=True, url="https://blog.example.com/post-1")
        assert r.success is True
        assert r.error is None

    def test_failure(self) -> None:
        r = PublishResult(platform="linkedin", success=False, error="Rate limited")
        assert r.success is False
        assert r.error == "Rate limited"
        assert r.post_id is None
        assert r.url is None


class TestBackwardsCompatibility:
    """Models imported from publishers.base must still work (re-export check)."""

    def test_import_from_publishers_base(self) -> None:
        from agent.publishers.base import ArticleSummary as AS
        from agent.publishers.base import ContentPackage as CP
        from agent.publishers.base import PublishResult as PR

        assert AS is ArticleSummary
        assert CP is ContentPackage
        assert PR is PublishResult
