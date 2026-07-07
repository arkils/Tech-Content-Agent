"""
tests/test_deduplication.py
============================
Unit tests for agent/tools/deduplication.py.

DynamoDB is mocked with moto throughout.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import boto3
import pytest
from moto import mock_aws

from agent.config import AgentConfig
from agent.models import Article
from agent.tools.deduplication import ArticleDeduplicator, _chunks, _ttl_timestamp


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_article(n: int) -> Article:
    return Article(
        url=f"https://example.com/article-{n}",
        title=f"Article {n}",
        source="Test Source",
    )


def _make_table(client: object) -> None:
    client.create_table(
        TableName=AgentConfig.dynamodb_table_name,
        KeySchema=[{"AttributeName": "url", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "url", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


def _seed_url(client: object, url: str, processed_at: datetime | None = None) -> None:
    """Write a minimal seen-article record to the moto table."""
    client.put_item(
        TableName=AgentConfig.dynamodb_table_name,
        Item={
            "url": {"S": url},
            "title": {"S": "Seen Article"},
            "source": {"S": "Some Source"},
            "processed_at": {"S": (processed_at or datetime.now(timezone.utc)).isoformat()},
            "ttl": {"N": str(_ttl_timestamp(90))},
        },
    )


# ---------------------------------------------------------------------------
# filter_new
# ---------------------------------------------------------------------------


@mock_aws
class TestFilterNew:
    def test_returns_all_when_none_seen(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2)]

        result = dedup.filter_new(articles)

        assert len(result) == 2

    def test_filters_out_seen_articles(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        _seed_url(client, "https://example.com/article-1")
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2)]

        result = dedup.filter_new(articles)

        assert len(result) == 1
        assert result[0].url == "https://example.com/article-2"

    def test_returns_empty_when_all_seen(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        _seed_url(client, "https://example.com/article-1")
        _seed_url(client, "https://example.com/article-2")
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2)]

        result = dedup.filter_new(articles)

        assert result == []

    def test_returns_empty_list_for_empty_input(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)

        result = dedup.filter_new([])

        assert result == []

    def test_ignores_entries_older_than_one_day(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        old_seen_at = datetime.now(timezone.utc) - timedelta(days=2)
        _seed_url(client, "https://example.com/article-1", processed_at=old_seen_at)
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2)]

        result = dedup.filter_new(articles)

        assert len(result) == 2

    def test_preserves_article_order(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        _seed_url(client, "https://example.com/article-2")
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2), _make_article(3)]

        result = dedup.filter_new(articles)

        assert [a.url for a in result] == [
            "https://example.com/article-1",
            "https://example.com/article-3",
        ]

    def test_handles_large_batch_over_100_urls(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        # Seed the first 50 URLs as already seen
        for i in range(50):
            _seed_url(client, f"https://example.com/article-{i}")
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(i) for i in range(120)]

        result = dedup.filter_new(articles)

        assert len(result) == 70
        for a in result:
            assert int(a.url.split("-")[-1]) >= 50


# ---------------------------------------------------------------------------
# mark_seen
# ---------------------------------------------------------------------------


@mock_aws
class TestMarkSeen:
    def test_writes_articles_to_dynamodb(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2)]

        dedup.mark_seen(articles)

        # Verify both URLs are now in the table
        for article in articles:
            response = client.get_item(
                TableName=AgentConfig.dynamodb_table_name,
                Key={"url": {"S": article.url}},
            )
            assert "Item" in response
            assert response["Item"]["url"]["S"] == article.url

    def test_written_item_has_title_and_source(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)
        article = Article(url="https://x.com/a", title="My Title", source="My Source")

        dedup.mark_seen([article])

        item = client.get_item(
            TableName=AgentConfig.dynamodb_table_name,
            Key={"url": {"S": "https://x.com/a"}},
        )["Item"]
        assert item["title"]["S"] == "My Title"
        assert item["source"]["S"] == "My Source"

    def test_written_item_has_ttl(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)

        dedup.mark_seen([_make_article(1)])

        item = client.get_item(
            TableName=AgentConfig.dynamodb_table_name,
            Key={"url": {"S": "https://example.com/article-1"}},
        )["Item"]
        ttl_value = int(item["ttl"]["N"])
        assert ttl_value > 0

    def test_written_item_has_processed_at(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)

        dedup.mark_seen([_make_article(1)])

        item = client.get_item(
            TableName=AgentConfig.dynamodb_table_name,
            Key={"url": {"S": "https://example.com/article-1"}},
        )["Item"]
        assert "processed_at" in item

    def test_no_op_for_empty_list(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)

        # Should not raise
        dedup.mark_seen([])

    def test_round_trip_filter_then_mark(self) -> None:
        """Articles marked seen should be filtered out on the next call."""
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        dedup = ArticleDeduplicator(dynamodb_client=client)
        articles = [_make_article(1), _make_article(2)]

        # First run: all new
        new = dedup.filter_new(articles)
        assert len(new) == 2

        # Mark as seen
        dedup.mark_seen(new)

        # Second run: all filtered out
        new_again = dedup.filter_new(articles)
        assert new_again == []


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestChunks:
    def test_splits_evenly(self) -> None:
        result = list(_chunks([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_handles_remainder(self) -> None:
        result = list(_chunks([1, 2, 3], 2))
        assert result == [[1, 2], [3]]

    def test_empty_list(self) -> None:
        assert list(_chunks([], 10)) == []

    def test_chunk_larger_than_list(self) -> None:
        result = list(_chunks([1, 2], 100))
        assert result == [[1, 2]]


class TestTtlTimestamp:
    def test_returns_future_timestamp(self) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        ttl = _ttl_timestamp(90)
        assert ttl > now

    def test_ttl_approx_correct_days(self) -> None:
        now = int(datetime.now(timezone.utc).timestamp())
        ttl = _ttl_timestamp(90)
        diff_days = (ttl - now) / 86400
        assert 89 < diff_days < 91
