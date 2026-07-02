"""
agent/tools/news_fetcher.py
===========================
``fetch_tech_news`` tool — RSS feed ingestion with DynamoDB-backed feed registry.

Feed source resolution (hybrid strategy)
-----------------------------------------
1. Query DynamoDB ``AgentConfig.news_feeds_table`` for records where
   ``enabled = true``.  This allows feeds to be managed at runtime without
   redeployment.
2. If the table is empty **or** DynamoDB is unreachable, fall back to
   ``AgentConfig.news_feed_urls`` (env var or hardcoded defaults).

The tool parses each feed with ``feedparser``, deduplicates by URL within the
batch, and caps the result at ``AgentConfig.max_articles_per_run``.

Usage::

    import boto3
    from agent.tools.news_fetcher import NewsFetcher

    fetcher = NewsFetcher(dynamodb_client=boto3.client("dynamodb"))
    articles = fetcher.run()
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import feedparser

from agent.config import AgentConfig
from agent.models import Article, FeedSource

if TYPE_CHECKING:
    from mypy_boto3_dynamodb import DynamoDBClient

logger = logging.getLogger(__name__)


class NewsFetcher:
    """
    Fetches tech news articles from RSS/Atom feeds.

    Inject a boto3 DynamoDB *client* (not resource) so tests can mock it
    with moto without patching module globals.

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

    def run(self) -> list[Article]:
        """
        Fetch and return tech news articles.

        Returns:
            Deduplicated list of articles, capped at
            ``AgentConfig.max_articles_per_run``.
        """
        sources = self._load_feed_sources()
        logger.info("Fetching from %d feed source(s)", len(sources))

        articles = self._fetch_articles(sources)
        articles = _deduplicate(articles)

        cap = self._config.max_articles_per_run
        if len(articles) > cap:
            logger.info("Capping articles from %d to %d", len(articles), cap)
            articles = articles[:cap]

        logger.info("Returning %d article(s)", len(articles))
        return articles

    # ------------------------------------------------------------------
    # Feed source resolution
    # ------------------------------------------------------------------

    def _load_feed_sources(self) -> list[FeedSource]:
        """Return enabled feed sources from DynamoDB, falling back to config."""
        try:
            sources = self._scan_dynamodb_feeds()
        except Exception:
            logger.warning(
                "DynamoDB feed registry unavailable — falling back to config URLs",
                exc_info=True,
            )
            sources = []

        if not sources:
            logger.info("No feeds in DynamoDB — using config fallback URLs")
            sources = [FeedSource.from_url(url) for url in self._config.news_feed_urls]

        return sources

    def _scan_dynamodb_feeds(self) -> list[FeedSource]:
        """
        Scan the feed registry table and return only enabled sources.

        Each DynamoDB item must have at minimum a ``feed_url`` (S) attribute.
        Optional attributes: ``name`` (S), ``category`` (S), ``enabled`` (BOOL).
        """
        response = self._ddb.scan(
            TableName=self._config.news_feeds_table,
            FilterExpression="enabled = :true",
            ExpressionAttributeValues={":true": {"BOOL": True}},
        )
        items = response.get("Items", [])
        logger.debug("DynamoDB scan returned %d feed item(s)", len(items))

        sources: list[FeedSource] = []
        for item in items:
            feed_url = item.get("feed_url", {}).get("S", "")
            if not feed_url:
                logger.warning("Skipping DynamoDB feed item with missing feed_url: %s", item)
                continue
            sources.append(
                FeedSource(
                    feed_url=feed_url,
                    name=item.get("name", {}).get("S", ""),
                    category=item.get("category", {}).get("S", "general"),
                    enabled=True,
                )
            )
        return sources

    # ------------------------------------------------------------------
    # RSS parsing
    # ------------------------------------------------------------------

    def _fetch_articles(self, sources: list[FeedSource]) -> list[Article]:
        """Parse each feed source and aggregate the resulting articles."""
        articles: list[Article] = []
        for source in sources:
            try:
                batch = self._parse_feed(source)
                logger.debug("Parsed %d article(s) from %s", len(batch), source.feed_url)
                articles.extend(batch)
            except Exception:
                logger.warning(
                    "Failed to parse feed %s — skipping", source.feed_url, exc_info=True
                )
        return articles

    def _parse_feed(self, source: FeedSource) -> list[Article]:
        """Parse a single RSS/Atom feed and return a list of Articles."""
        parsed = feedparser.parse(source.feed_url)

        if parsed.get("bozo") and not parsed.get("entries"):
            raise ValueError(
                f"feedparser reported a malformed feed at {source.feed_url}: "
                f"{parsed.get('bozo_exception')}"
            )

        feed_name = source.name or parsed.feed.get("title", source.feed_url)
        articles: list[Article] = []

        for entry in parsed.get("entries", []):
            url = entry.get("link", "")
            title = entry.get("title", "")
            if not url or not title:
                continue

            content = _extract_content(entry)
            published_at = _parse_published(entry)

            articles.append(
                Article(
                    url=url,
                    title=title,
                    source=feed_name,
                    published_at=published_at,
                    content=content,
                )
            )

        return articles


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _extract_content(entry: object) -> str:
    """Extract the best available body text from a feedparser entry."""
    content_list = getattr(entry, "content", None)
    if content_list:
        return content_list[0].get("value", "")
    return entry.get("summary", "")  # type: ignore[union-attr]


def _parse_published(entry: object) -> datetime | None:
    """Convert feedparser's ``published_parsed`` time struct to a UTC datetime."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")  # type: ignore[union-attr]
    if struct is None:
        return None
    try:
        return datetime(*struct[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _deduplicate(articles: list[Article]) -> list[Article]:
    """Remove duplicate articles by URL, preserving insertion order."""
    seen: set[str] = set()
    unique: list[Article] = []
    for article in articles:
        if article.url not in seen:
            seen.add(article.url)
            unique.append(article)
    return unique
