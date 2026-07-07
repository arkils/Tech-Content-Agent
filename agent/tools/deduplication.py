"""
agent/tools/deduplication.py
=============================
``check_duplicate`` tool — DynamoDB-backed article URL deduplication.

This tool serves two roles in the pipeline:

1. **Filter** (before summarisation) — ``filter_new()`` takes the raw
   ``Article`` list from ``fetch_tech_news`` and returns only those whose
   URLs have not been seen in a previous pipeline run.

2. **Record** (after publishing) — ``mark_seen()`` writes the successfully
   processed article URLs to DynamoDB so future runs skip them.

DynamoDB table schema (``AgentConfig.dynamodb_table_name``)
------------------------------------------------------------
Partition key: ``url`` (String)

Additional attributes written by ``mark_seen``::

    {
        "url":          "https://example.com/article",   # PK
        "title":        "Article headline",
        "source":       "Ars Technica",
        "processed_at": "2026-07-02T09:00:00+00:00",    # ISO-8601 UTC
        "ttl":          1751443200                        # Unix epoch; DynamoDB auto-deletes after this
    }

TTL is controlled by ``AgentConfig.article_ttl_days`` (default 90 days).
DynamoDB TTL deletion is eventually consistent — items may linger for up to
48 hours after expiry, which is acceptable for this use case.

Usage::

    import boto3
    from agent.tools.deduplication import ArticleDeduplicator

    dedup = ArticleDeduplicator(dynamodb_client=boto3.client("dynamodb"))
    new_articles = dedup.filter_new(all_articles)
    # ... summarise and publish ...
    dedup.mark_seen(new_articles)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from agent.config import AgentConfig
from agent.models import Article

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DYNAMODB_BATCH_WRITE_LIMIT = 25  # DynamoDB hard limit per batch_write_item call
_DYNAMODB_BATCH_GET_LIMIT = 100   # DynamoDB hard limit per batch_get_item call
_RECENT_SEEN_WINDOW_DAYS = 1


class ArticleDeduplicator:
    """
    Checks and records processed article URLs in DynamoDB.

    Inject a boto3 DynamoDB *client* so tests can mock it with moto.

    Args:
        dynamodb_client: A ``boto3.client("dynamodb")`` instance.
        config:          Agent configuration; defaults to ``AgentConfig``.
    """

    def __init__(
        self,
        dynamodb_client: object,
        config: type[AgentConfig] = AgentConfig,
    ) -> None:
        self._ddb = dynamodb_client
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def filter_new(self, articles: list[Article]) -> list[Article]:
        """
        Return only articles whose URLs have not been seen before.

        Uses ``BatchGetItem`` to check DynamoDB in batches of up to 100 keys.
        On DynamoDB error the exception propagates — the pipeline should treat
        a failed dedup check as a hard stop rather than silently re-publishing.

        Args:
            articles: Raw articles from ``fetch_tech_news``.

        Returns:
            Subset of ``articles`` that are not yet in the DynamoDB table.
        """
        if not articles:
            return []

        existing_urls = self._fetch_existing_urls([a.url for a in articles])
        new_articles = [a for a in articles if a.url not in existing_urls]

        logger.info(
            "Deduplication: %d total, %d already seen, %d new",
            len(articles),
            len(articles) - len(new_articles),
            len(new_articles),
        )
        return new_articles

    def mark_seen(self, articles: list[Article]) -> None:
        """
        Record article URLs in DynamoDB to prevent future re-processing.

        Uses ``BatchWriteItem`` in chunks of 25 (DynamoDB limit).  Each item
        is written with a TTL so old records are automatically purged.

        Args:
            articles: Articles that were successfully processed this run.
        """
        if not articles:
            return

        ttl = _ttl_timestamp(self._config.article_ttl_days)
        now = datetime.now(timezone.utc).isoformat()

        requests = [
            {
                "PutRequest": {
                    "Item": {
                        "url": {"S": article.url},
                        "title": {"S": article.title},
                        "source": {"S": article.source},
                        "processed_at": {"S": now},
                        "ttl": {"N": str(ttl)},
                    }
                }
            }
            for article in articles
        ]

        for batch in _chunks(requests, _DYNAMODB_BATCH_WRITE_LIMIT):
            self._ddb.batch_write_item(
                RequestItems={self._config.dynamodb_table_name: batch}
            )

        logger.info("Marked %d article(s) as seen in DynamoDB", len(articles))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_existing_urls(self, urls: list[str]) -> set[str]:
        """
        Batch-fetch URLs from DynamoDB and return those that were seen recently.

        Entries remain in the table for the full TTL retention window, but only
        items newer than the recent-seen window are treated as duplicates for
        the next scheduled run.
        """
        existing: set[str] = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=_RECENT_SEEN_WINDOW_DAYS)

        for batch in _chunks(urls, _DYNAMODB_BATCH_GET_LIMIT):
            keys = [{"url": {"S": url}} for url in batch]
            response = self._ddb.batch_get_item(
                RequestItems={
                    self._config.dynamodb_table_name: {"Keys": keys}
                }
            )
            for item in response.get("Responses", {}).get(
                self._config.dynamodb_table_name, []
            ):
                url_val = item.get("url", {}).get("S", "")
                processed_at = item.get("processed_at", {}).get("S", "")
                if not url_val:
                    continue
                if not processed_at:
                    continue
                try:
                    seen_at = datetime.fromisoformat(processed_at)
                except ValueError:
                    continue
                if seen_at >= cutoff:
                    existing.add(url_val)

        return existing


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _chunks(items: list, size: int) -> list:
    """Split ``items`` into consecutive chunks of at most ``size`` elements."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _ttl_timestamp(ttl_days: int) -> int:
    """Return a Unix epoch timestamp ``ttl_days`` from now (UTC)."""
    expiry = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    return int(expiry.timestamp())
