"""
tests/test_news_pipeline.py
============================
Integration-style unit tests for agent/workflows/news_pipeline.py.

All AWS services (DynamoDB, Bedrock) are mocked.  The pipeline is driven
end-to-end so each test verifies the full orchestration logic.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

from agent.config import AgentConfig
from agent.models import Article, ArticleSummary
from agent.workflows.news_pipeline import NewsPipeline, PipelineResult


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_FEED_RESPONSE = MagicMock()
_FEED_RESPONSE.get.side_effect = lambda key, default=None: {
    "bozo": False,
    "entries": [
        {
            "link": "https://example.com/article-1",
            "title": "AI Breakthrough",
            "summary": "Summary of AI article.",
            "published_parsed": None,
        },
        {
            "link": "https://example.com/article-2",
            "title": "Cloud Computing News",
            "summary": "Summary of cloud article.",
            "published_parsed": None,
        },
    ],
}.get(key, default)
_FEED_RESPONSE.feed = MagicMock()
_FEED_RESPONSE.feed.get.return_value = "Mock Feed"

_BEDROCK_SUMMARIES = [
    {
        "title": "AI Breakthrough",
        "url": "https://example.com/article-1",
        "summary": "AI has made significant strides.",
        "relevance_score": 5,
        "duplicate_of": None,
    },
    {
        "title": "Cloud Computing News",
        "url": "https://example.com/article-2",
        "summary": "Cloud providers expand globally.",
        "relevance_score": 3,
        "duplicate_of": None,
    },
]

_BEDROCK_POST = "Today in tech: AI is reshaping everything. #AI #Tech"


def _make_dynamodb_tables(client: object) -> None:
    """Create both DynamoDB tables needed by the pipeline."""
    for table_name, pk in [
        (AgentConfig.dynamodb_table_name, "url"),
        (AgentConfig.news_feeds_table, "feed_url"),
    ]:
        client.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": pk, "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )


def _make_bedrock_client(summaries: list[dict], post: str) -> MagicMock:
    """Return a mock Bedrock client that returns summaries then the post text."""
    client = MagicMock()
    client.converse.side_effect = [
        # First call: summarise_articles
        {"output": {"message": {"content": [{"text": json.dumps(summaries)}]}}},
        # Second call: generate_post
        {"output": {"message": {"content": [{"text": post}]}}},
    ]
    return client


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


@mock_aws
class TestNewsPipelineRun:
    def test_returns_pipeline_result(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert isinstance(result, PipelineResult)

    def test_articles_fetched_count(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.articles_fetched > 0

    def test_summaries_produced(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.summaries_produced == len(_BEDROCK_SUMMARIES)

    def test_not_skipped_on_new_articles(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.skipped is False

    def test_publish_results_populated(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert len(result.publish_results) == len(AgentConfig.enabled_publishers)

    def test_articles_marked_seen_after_run(self) -> None:
        """Articles processed in run() should be in DynamoDB after completion."""
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        item = ddb.get_item(
            TableName=AgentConfig.dynamodb_table_name,
            Key={"url": {"S": "https://example.com/article-1"}},
        )
        assert "Item" in item


# ---------------------------------------------------------------------------
# Early-exit: no new articles
# ---------------------------------------------------------------------------


@mock_aws
class TestPipelineEarlyExitNoNewArticles:
    def test_skipped_when_all_articles_seen(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        # Pre-seed both articles as already seen
        for url in ["https://example.com/article-1", "https://example.com/article-2"]:
            ddb.put_item(
                TableName=AgentConfig.dynamodb_table_name,
                Item={
                    "url": {"S": url},
                    "title": {"S": "Seen"},
                    "source": {"S": "Test"},
                    "processed_at": {"S": "2026-07-01T00:00:00+00:00"},
                    "ttl": {"N": "9999999999"},
                },
            )
        bedrock = MagicMock()

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.skipped is True
        assert "deduplication" in result.skip_reason.lower()
        bedrock.converse.assert_not_called()

    def test_articles_new_is_zero_when_all_seen(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        for url in ["https://example.com/article-1", "https://example.com/article-2"]:
            ddb.put_item(
                TableName=AgentConfig.dynamodb_table_name,
                Item={
                    "url": {"S": url},
                    "title": {"S": "Seen"},
                    "source": {"S": "Test"},
                    "processed_at": {"S": "2026-07-01T00:00:00+00:00"},
                    "ttl": {"N": "9999999999"},
                },
            )

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(
                dynamodb_client=ddb, bedrock_client=MagicMock()
            ).run()

        assert result.articles_new == 0

    def test_force_no_new_articles_allows_duplicate_processing(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        for url in ["https://example.com/article-1", "https://example.com/article-2"]:
            ddb.put_item(
                TableName=AgentConfig.dynamodb_table_name,
                Item={
                    "url": {"S": url},
                    "title": {"S": "Seen"},
                    "source": {"S": "Test"},
                    "processed_at": {"S": "2026-07-01T00:00:00+00:00"},
                    "ttl": {"N": "9999999999"},
                },
            )
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch.dict(os.environ, {"FORCE_NO_NEW_ARTICLES": "true"}, clear=False):
            with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
                with patch("agent.tools.bedrock_summariser.ArticleSummariser._call_bedrock") as mock_call:
                    mock_call.return_value = json.dumps(_BEDROCK_SUMMARIES)
                    with patch("agent.tools.post_generator.PostGenerator._call_bedrock") as mock_post_call:
                        mock_post_call.return_value = _BEDROCK_POST
                        result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.skipped is False
        assert result.summaries_produced == len(_BEDROCK_SUMMARIES)
        assert result.articles_new == 2


# ---------------------------------------------------------------------------
# Early-exit: no summaries from Bedrock
# ---------------------------------------------------------------------------


@mock_aws
class TestPipelineEarlyExitNoSummaries:
    def test_skipped_when_bedrock_returns_no_summaries(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = MagicMock()
        bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "[]"}]}}
        }

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.skipped is True
        assert "summarisation" in result.skip_reason.lower()

    def test_no_publish_results_when_skipped_at_summarise(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = MagicMock()
        bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "[]"}]}}
        }

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        assert result.publish_results == []


# ---------------------------------------------------------------------------
# Publisher failure resilience
# ---------------------------------------------------------------------------


@mock_aws
class TestPipelinePublisherFailure:
    def test_failed_publisher_does_not_stop_pipeline(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            with patch(
                "agent.publishers.blog.BlogPublisher.publish",
                side_effect=RuntimeError("disk full"),
            ):
                result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        # Pipeline should complete and return a result with a failed publish entry
        assert isinstance(result, PipelineResult)
        assert any(not r.success for r in result.publish_results)

    def test_failed_publisher_result_has_error_message(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            with patch(
                "agent.publishers.blog.BlogPublisher.publish",
                side_effect=RuntimeError("disk full"),
            ):
                result = NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        failed = [r for r in result.publish_results if not r.success]
        assert len(failed) >= 1
        assert failed[0].error is not None


# ---------------------------------------------------------------------------
# Second run deduplication
# ---------------------------------------------------------------------------


@mock_aws
class TestPipelineSecondRun:
    def test_second_run_skips_already_processed_articles(self) -> None:
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        _make_dynamodb_tables(ddb)
        bedrock = _make_bedrock_client(_BEDROCK_SUMMARIES, _BEDROCK_POST)

        # First run
        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            NewsPipeline(dynamodb_client=ddb, bedrock_client=bedrock).run()

        # Second run — same feed, same articles, should be skipped
        with patch("agent.tools.news_fetcher.feedparser.parse", return_value=_FEED_RESPONSE):
            result2 = NewsPipeline(
                dynamodb_client=ddb, bedrock_client=MagicMock()
            ).run()

        assert result2.skipped is True
        assert result2.articles_new == 0
