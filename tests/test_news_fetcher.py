"""
tests/test_news_fetcher.py
==========================
Unit tests for agent/tools/news_fetcher.py.

DynamoDB is mocked with moto.
RSS feed HTTP calls are mocked by patching feedparser.parse directly so tests
run fully offline with no network dependency.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from agent.config import AgentConfig
from agent.models import Article
from agent.tools.news_fetcher import NewsFetcher, _deduplicate, _extract_content, _parse_published


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RSS_ENTRY_1 = {
    "link": "https://example.com/article-1",
    "title": "AI Takes Over",
    "summary": "Summary of article 1.",
    "published_parsed": time.strptime("2026-07-01", "%Y-%m-%d"),
}

_RSS_ENTRY_2 = {
    "link": "https://example.com/article-2",
    "title": "Cloud Wars Continue",
    "summary": "Summary of article 2.",
    "published_parsed": time.strptime("2026-07-02", "%Y-%m-%d"),
}


def _make_parsed_feed(entries: list[dict], bozo: bool = False) -> MagicMock:
    """Build a minimal feedparser result mock."""
    feed_meta = MagicMock()
    feed_meta.get.return_value = "Mock Feed"
    mock = MagicMock()
    mock.get.side_effect = lambda key, default=None: {
        "bozo": bozo,
        "entries": entries,
    }.get(key, default)
    mock.feed = feed_meta
    return mock


def _make_dynamodb_client(table_name: str) -> object:
    """Create a real (moto-backed) DynamoDB client with the feeds table."""
    client = boto3.client("dynamodb", region_name="us-east-1")
    client.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "feed_url", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "feed_url", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    return client


# ---------------------------------------------------------------------------
# DynamoDB feed source resolution
# ---------------------------------------------------------------------------


@mock_aws
class TestLoadFeedSourcesFromDynamoDB:
    def test_returns_enabled_feeds_from_dynamo(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)
        client.put_item(
            TableName=AgentConfig.news_feeds_table,
            Item={
                "feed_url": {"S": "https://feeds.example.com/rss"},
                "name": {"S": "Example Feed"},
                "category": {"S": "general"},
                "enabled": {"BOOL": True},
            },
        )
        fetcher = NewsFetcher(dynamodb_client=client)
        sources = fetcher._load_feed_sources()

        assert len(sources) == 1
        assert sources[0].feed_url == "https://feeds.example.com/rss"
        assert sources[0].name == "Example Feed"
        assert sources[0].enabled is True

    def test_skips_disabled_feeds(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)
        client.put_item(
            TableName=AgentConfig.news_feeds_table,
            Item={
                "feed_url": {"S": "https://feeds.example.com/disabled"},
                "name": {"S": "Disabled Feed"},
                "enabled": {"BOOL": False},
            },
        )
        fetcher = NewsFetcher(dynamodb_client=client)
        # Disabled feeds are excluded by the FilterExpression; empty table
        # triggers fallback to config URLs.
        sources = fetcher._load_feed_sources()
        # Should fall back to AgentConfig defaults (no disabled feed in list)
        urls = [s.feed_url for s in sources]
        assert "https://feeds.example.com/disabled" not in urls

    def test_falls_back_to_config_when_table_empty(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)
        fetcher = NewsFetcher(dynamodb_client=client)
        sources = fetcher._load_feed_sources()

        assert len(sources) == len(AgentConfig.news_feed_urls)
        assert sources[0].feed_url == AgentConfig.news_feed_urls[0]

    def test_falls_back_to_config_on_ddb_error(self) -> None:
        bad_client = MagicMock()
        bad_client.scan.side_effect = Exception("DynamoDB unavailable")
        fetcher = NewsFetcher(dynamodb_client=bad_client)
        sources = fetcher._load_feed_sources()

        assert len(sources) == len(AgentConfig.news_feed_urls)

    def test_skips_dynamo_item_with_empty_feed_url(self) -> None:
        # DynamoDB rejects empty/missing partition keys, but we mock the scan
        # response directly to verify the fetcher's defensive guard still applies
        # if a malformed item somehow appears (e.g. via a direct SDK bypass).
        client = MagicMock()
        client.scan.return_value = {
            "Items": [{"name": {"S": "Bad Item"}, "enabled": {"BOOL": True}}]
        }
        fetcher = NewsFetcher(dynamodb_client=client)
        sources = fetcher._scan_dynamodb_feeds()
        assert sources == []


# ---------------------------------------------------------------------------
# RSS parsing
# ---------------------------------------------------------------------------


class TestParseFeed:
    def test_returns_articles_from_feed(self) -> None:
        client = MagicMock()
        fetcher = NewsFetcher(dynamodb_client=client)
        from agent.models import FeedSource

        source = FeedSource(feed_url="https://feeds.example.com/rss", name="Example")
        mock_feed = _make_parsed_feed([_RSS_ENTRY_1, _RSS_ENTRY_2])

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher._parse_feed(source)

        assert len(articles) == 2
        assert articles[0].url == "https://example.com/article-1"
        assert articles[0].title == "AI Takes Over"
        assert articles[0].source == "Example"

    def test_skips_entries_without_url(self) -> None:
        client = MagicMock()
        fetcher = NewsFetcher(dynamodb_client=client)
        from agent.models import FeedSource

        source = FeedSource(feed_url="https://feeds.example.com/rss")
        bad_entry = {"title": "No URL Here", "summary": "..."}
        mock_feed = _make_parsed_feed([bad_entry])

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher._parse_feed(source)

        assert articles == []

    def test_skips_entries_without_title(self) -> None:
        client = MagicMock()
        fetcher = NewsFetcher(dynamodb_client=client)
        from agent.models import FeedSource

        source = FeedSource(feed_url="https://feeds.example.com/rss")
        bad_entry = {"link": "https://example.com/no-title", "summary": "..."}
        mock_feed = _make_parsed_feed([bad_entry])

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher._parse_feed(source)

        assert articles == []

    def test_raises_on_bozo_feed_with_no_entries(self) -> None:
        client = MagicMock()
        fetcher = NewsFetcher(dynamodb_client=client)
        from agent.models import FeedSource

        source = FeedSource(feed_url="https://feeds.example.com/broken")
        mock_feed = _make_parsed_feed([], bozo=True)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            with pytest.raises(ValueError, match="malformed feed"):
                fetcher._parse_feed(source)

    def test_uses_feed_title_as_source_when_name_empty(self) -> None:
        client = MagicMock()
        fetcher = NewsFetcher(dynamodb_client=client)
        from agent.models import FeedSource

        source = FeedSource(feed_url="https://feeds.example.com/rss", name="")
        mock_feed = _make_parsed_feed([_RSS_ENTRY_1])
        mock_feed.feed.get.return_value = "Parsed Feed Title"

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher._parse_feed(source)

        assert articles[0].source == "Parsed Feed Title"


# ---------------------------------------------------------------------------
# run() integration
# ---------------------------------------------------------------------------


@mock_aws
class TestNewsFetcherRun:
    def test_run_returns_list_of_articles(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)
        fetcher = NewsFetcher(dynamodb_client=client)
        mock_feed = _make_parsed_feed([_RSS_ENTRY_1, _RSS_ENTRY_2])

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher.run()

        assert isinstance(articles, list)
        assert all(isinstance(a, Article) for a in articles)

    def test_run_caps_at_max_articles(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)

        class CapConfig(AgentConfig):
            max_articles_per_run: int = 1

        fetcher = NewsFetcher(dynamodb_client=client, config=CapConfig)
        mock_feed = _make_parsed_feed([_RSS_ENTRY_1, _RSS_ENTRY_2])

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher.run()

        assert len(articles) <= 1

    def test_run_skips_failed_feeds_and_continues(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)
        fetcher = NewsFetcher(dynamodb_client=client)

        def side_effect(url: str) -> MagicMock:
            if "arstechnica" in url:
                raise ConnectionError("timeout")
            return _make_parsed_feed([_RSS_ENTRY_1])

        with patch("agent.tools.news_fetcher.feedparser.parse", side_effect=side_effect):
            articles = fetcher.run()

        # Should still return articles from feeds that didn't fail
        assert isinstance(articles, list)

    def test_run_deduplicates_across_feeds(self) -> None:
        client = _make_dynamodb_client(AgentConfig.news_feeds_table)
        fetcher = NewsFetcher(dynamodb_client=client)
        # Same entry returned by every feed
        mock_feed = _make_parsed_feed([_RSS_ENTRY_1])

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetcher.run()

        urls = [a.url for a in articles]
        assert len(urls) == len(set(urls))


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_removes_duplicate_urls(self) -> None:
        a1 = Article(url="https://x.com/1", title="A")
        a2 = Article(url="https://x.com/1", title="A duplicate")
        a3 = Article(url="https://x.com/2", title="B")
        result = _deduplicate([a1, a2, a3])
        assert len(result) == 2
        assert result[0].url == "https://x.com/1"
        assert result[1].url == "https://x.com/2"

    def test_preserves_insertion_order(self) -> None:
        articles = [Article(url=f"https://x.com/{i}", title=str(i)) for i in range(5)]
        result = _deduplicate(articles)
        assert [a.url for a in result] == [a.url for a in articles]

    def test_empty_list(self) -> None:
        assert _deduplicate([]) == []


class TestParsePublished:
    def test_parses_valid_struct(self) -> None:
        struct = time.strptime("2026-07-01", "%Y-%m-%d")
        result = _parse_published({"published_parsed": struct})
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2026

    def test_returns_none_for_missing_date(self) -> None:
        assert _parse_published({}) is None

    def test_falls_back_to_updated_parsed(self) -> None:
        struct = time.strptime("2026-06-15", "%Y-%m-%d")
        result = _parse_published({"updated_parsed": struct})
        assert result is not None
        assert result.month == 6


class TestExtractContent:
    def test_prefers_content_over_summary(self) -> None:
        entry = MagicMock()
        entry.content = [{"value": "Full content"}]
        entry.get.return_value = "Summary text"
        assert _extract_content(entry) == "Full content"

    def test_falls_back_to_summary(self) -> None:
        entry = {"summary": "Just a summary"}
        assert _extract_content(entry) == "Just a summary"

    def test_returns_empty_string_when_no_content(self) -> None:
        assert _extract_content({}) == ""
