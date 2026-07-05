"""
tests/tools/test_post_tracker.py
=================================
Unit tests for agent/tools/post_tracker.py.

DynamoDB is mocked with moto throughout.
"""

from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from agent.config import AgentConfig
from agent.tools.post_tracker import PostTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_table(client: object) -> None:
    client.create_table(
        TableName=AgentConfig.posts_table_name,
        KeySchema=[{"AttributeName": "post_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "post_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )


def _get_item(client: object, post_id: str) -> dict:
    response = client.get_item(
        TableName=AgentConfig.posts_table_name,
        Key={"post_id": {"S": post_id}},
    )
    return response["Item"]


# ---------------------------------------------------------------------------
# create_pending
# ---------------------------------------------------------------------------


@mock_aws
class TestCreatePending:
    def test_returns_uuid_string(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "post content", "AI news")

        assert isinstance(post_id, str)
        assert len(post_id) == 36  # UUID v4 format

    def test_writes_pending_status(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "post content", "AI news")
        item = _get_item(client, post_id)

        assert item["status"]["S"] == "pending"

    def test_writes_correct_platform_and_topic(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "hello world", "Tech digest")
        item = _get_item(client, post_id)

        assert item["platform"]["S"] == "linkedin"
        assert item["topic"]["S"] == "Tech digest"
        assert item["content"]["S"] == "hello world"

    def test_writes_created_at_and_ttl(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        item = _get_item(client, post_id)

        assert "created_at" in item
        assert "ttl" in item
        assert int(item["ttl"]["N"]) > 0


# ---------------------------------------------------------------------------
# mark_success
# ---------------------------------------------------------------------------


@mock_aws
class TestMarkSuccess:
    def test_updates_status_to_success(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_success(post_id, "urn:li:share:123", None)
        item = _get_item(client, post_id)

        assert item["status"]["S"] == "success"

    def test_sets_published_at(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_success(post_id, "urn:li:share:123", None)
        item = _get_item(client, post_id)

        assert "published_at" in item

    def test_sets_platform_post_id_when_provided(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_success(post_id, "urn:li:share:999", "https://linkedin.com/post/999")
        item = _get_item(client, post_id)

        assert item["platform_post_id"]["S"] == "urn:li:share:999"
        assert item["platform_url"]["S"] == "https://linkedin.com/post/999"

    def test_skips_optional_fields_when_none(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_success(post_id, None, None)
        item = _get_item(client, post_id)

        assert "platform_post_id" not in item
        assert "platform_url" not in item


# ---------------------------------------------------------------------------
# mark_dry_run
# ---------------------------------------------------------------------------


@mock_aws
class TestMarkDryRun:
    def test_updates_status_to_dry_run(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_dry_run(post_id)
        item = _get_item(client, post_id)

        assert item["status"]["S"] == "dry_run"

    def test_sets_published_at(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_dry_run(post_id)
        item = _get_item(client, post_id)

        assert "published_at" in item


# ---------------------------------------------------------------------------
# mark_error
# ---------------------------------------------------------------------------


@mock_aws
class TestMarkError:
    def test_updates_status_to_error(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_error(post_id, "HTTP 429 Too Many Requests")
        item = _get_item(client, post_id)

        assert item["status"]["S"] == "error"

    def test_stores_error_message(self) -> None:
        client = boto3.client("dynamodb", region_name="us-east-1")
        _make_table(client)
        tracker = PostTracker(dynamodb_client=client)

        post_id = tracker.create_pending("linkedin", "content", "topic")
        tracker.mark_error(post_id, "HTTP 429 Too Many Requests")
        item = _get_item(client, post_id)

        assert item["error_message"]["S"] == "HTTP 429 Too Many Requests"
