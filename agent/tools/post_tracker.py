"""
agent/tools/post_tracker.py
============================
``PostTracker`` — DynamoDB-backed post status tracking.

Records each publish attempt before delivery (status=``pending``) and updates
the record after publishing to one of:

- ``success``  — delivered to the platform successfully.
- ``dry_run``  — post was generated but ``ENABLE_POSTING=false``.
- ``error``    — delivery failed; ``error_message`` contains the reason.

DynamoDB table schema (``AgentConfig.posts_table_name``)
-----------------------------------------------------------
Partition key: ``post_id`` (String — UUID v4)

Attributes written by ``create_pending``::

    {
        "post_id":    "uuid-v4",
        "platform":   "linkedin",
        "status":     "pending",
        "content":    "Formatted post text ...",
        "topic":      "Today's tech digest",
        "created_at": "2026-07-05T10:00:00+00:00",
        "ttl":        1785913200
    }

Attributes added or updated by the ``mark_*`` methods::

    "status":           "success" | "dry_run" | "error"
    "published_at":     "2026-07-05T10:01:00+00:00"  # success / dry_run
    "platform_post_id": "urn:li:share:12345"          # success only
    "platform_url":     "https://..."                 # success only (if available)
    "error_message":    "HTTP 429 ..."                # error only

Usage::

    import boto3
    from agent.tools.post_tracker import PostTracker

    tracker = PostTracker(dynamodb_client=boto3.client("dynamodb"))
    post_id = tracker.create_pending("linkedin", content, topic)
    # ... attempt publish ...
    tracker.mark_success(post_id, "urn:li:share:99", None)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from agent.config import AgentConfig

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBClient

logger = logging.getLogger(__name__)


class PostTracker:
    """
    Tracks the lifecycle of each publish attempt in DynamoDB.

    Inject a boto3 DynamoDB *client* (not resource) so tests can mock it
    with moto without patching module globals.

    Args:
        dynamodb_client: Pre-built boto3 DynamoDB client.
        config: Agent configuration; defaults to ``AgentConfig``.
    """

    def __init__(
        self,
        dynamodb_client: DynamoDBClient,
        config: type[AgentConfig] | AgentConfig = AgentConfig,
    ) -> None:
        self._client = dynamodb_client
        self._config = config() if isinstance(config, type) else config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_pending(self, platform: str, content: str, topic: str) -> str:
        """
        Write a ``pending`` post record to DynamoDB.

        Args:
            platform: Platform key (e.g. ``"linkedin"``).
            content:  Fully formatted post text ready for delivery.
            topic:    Short headline / topic from the ``ContentPackage``.

        Returns:
            The ``post_id`` UUID string — pass it to ``mark_*`` after publishing.
        """
        post_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        ttl = int((now + timedelta(days=self._config.post_ttl_days)).timestamp())

        self._client.put_item(
            TableName=self._config.posts_table_name,
            Item={
                "post_id":    {"S": post_id},
                "platform":   {"S": platform},
                "status":     {"S": "pending"},
                "content":    {"S": content},
                "topic":      {"S": topic},
                "created_at": {"S": now.isoformat()},
                "ttl":        {"N": str(ttl)},
            },
        )
        logger.info(
            "PostTracker: created pending record post_id=%s platform=%s", post_id, platform
        )
        return post_id

    def mark_success(
        self,
        post_id: str,
        platform_post_id: str | None,
        platform_url: str | None,
    ) -> None:
        """
        Update the record to ``success`` after a successful publish.

        Args:
            post_id:          The UUID returned by ``create_pending``.
            platform_post_id: The ID assigned by the platform (e.g. LinkedIn URN).
            platform_url:     Public URL of the published post (if available).
        """
        now = datetime.now(timezone.utc).isoformat()
        update_expr = "SET #st = :status, published_at = :published_at"
        expr_values: dict = {
            ":status":       {"S": "success"},
            ":published_at": {"S": now},
        }

        if platform_post_id:
            update_expr += ", platform_post_id = :ppid"
            expr_values[":ppid"] = {"S": platform_post_id}
        if platform_url:
            update_expr += ", platform_url = :purl"
            expr_values[":purl"] = {"S": platform_url}

        self._client.update_item(
            TableName=self._config.posts_table_name,
            Key={"post_id": {"S": post_id}},
            UpdateExpression=update_expr,
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues=expr_values,
        )
        logger.info("PostTracker: marked success post_id=%s", post_id)

    def mark_dry_run(self, post_id: str) -> None:
        """
        Update the record to ``dry_run`` when ``ENABLE_POSTING=false``.

        The post was fully generated but not delivered to the platform.

        Args:
            post_id: The UUID returned by ``create_pending``.
        """
        now = datetime.now(timezone.utc).isoformat()
        self._client.update_item(
            TableName=self._config.posts_table_name,
            Key={"post_id": {"S": post_id}},
            UpdateExpression="SET #st = :status, published_at = :published_at",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status":       {"S": "dry_run"},
                ":published_at": {"S": now},
            },
        )
        logger.info("PostTracker: marked dry_run post_id=%s", post_id)

    def mark_error(self, post_id: str, error_message: str) -> None:
        """
        Update the record to ``error`` when publish failed.

        Args:
            post_id:       The UUID returned by ``create_pending``.
            error_message: Human-readable error description.
        """
        self._client.update_item(
            TableName=self._config.posts_table_name,
            Key={"post_id": {"S": post_id}},
            UpdateExpression="SET #st = :status, error_message = :err",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status": {"S": "error"},
                ":err":    {"S": error_message},
            },
        )
        logger.info("PostTracker: marked error post_id=%s", post_id)
