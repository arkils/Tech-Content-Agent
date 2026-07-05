"""
agent/models/__init__.py
========================
Data model definitions for the tech-news-agent.

All inter-module data contracts are defined here as dataclasses so that
tools and workflows can import them without depending on the publisher layer.

The publisher layer (``agent/publishers/base.py``) re-exports ``ArticleSummary``,
``ContentPackage``, and ``PublishResult`` from here for backwards compatibility.

Models
------
- ``FeedSource``      — a news feed record stored in DynamoDB (feed registry).
- ``Article``         — a raw article fetched from a feed source.
- ``ArticleSummary``  — a single article after Bedrock summarisation.
- ``ContentPackage``  — platform-agnostic bundle passed to every publisher.
- ``PublishResult``   — result returned by a publisher after delivery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ---------------------------------------------------------------------------
# Feed registry
# ---------------------------------------------------------------------------


@dataclass
class FeedSource:
    """
    A news feed record loaded from DynamoDB (or the fallback URL list).

    Attributes:
        feed_url:  RSS/Atom URL — also the DynamoDB partition key.
        name:      Human-readable display name.
        category:  Optional grouping label (e.g. ``"aws"``, ``"general"``).
        enabled:   When ``False`` the feed is skipped at runtime.
    """

    feed_url: str
    name: str = ""
    category: str = "general"
    enabled: bool = True

    @classmethod
    def from_url(cls, url: str) -> FeedSource:
        """Create a minimal FeedSource from a plain URL (fallback path)."""
        return cls(feed_url=url)


# ---------------------------------------------------------------------------
# Pipeline models
# ---------------------------------------------------------------------------


@dataclass
class Article:
    """
    A raw news article fetched from a feed source before summarisation.

    Attributes:
        url:           Canonical article URL — used as the deduplication key.
        title:         Article headline.
        source:        Human-readable source name (e.g. ``"Ars Technica"``).
        published_at:  Publication timestamp (UTC).  ``None`` if unavailable.
        content:       Full article text or RSS description snippet.
    """

    url: str
    title: str
    source: str = ""
    published_at: datetime | None = None
    content: str = ""


@dataclass
class ArticleSummary:
    """A single article after Bedrock summarisation."""

    title: str
    url: str
    summary: str
    relevance_score: int  # 1–5
    source: str = ""


@dataclass
class ContentPackage:
    """
    Platform-agnostic content produced by the pipeline.

    The pipeline builds one ``ContentPackage`` per run and passes it to
    every enabled publisher.  Each publisher formats it independently for
    its target platform.

    Attributes:
        topic:      Short headline capturing the day's dominant tech theme.
        digest:     2–3 sentence overall digest for the entire batch.
        articles:   Individual article summaries with relevance scores.
        keywords:   Extracted tech keywords / topics for hashtags / tags.
        raw_post:   Pre-generated post text from Bedrock (may be refined
                    by each publisher's own prompt).
    """

    topic: str
    digest: str
    articles: list[ArticleSummary] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    raw_post: str = ""


@dataclass
class PublishResult:
    """
    Result returned by a publisher after attempting to deliver content.

    Attributes:
        platform:   String key identifying the publisher (e.g. ``"linkedin"``).
        success:    ``True`` if the content was delivered without error.
        post_id:    Platform-assigned ID for the published post, if available.
        url:        Public URL of the published post, if available.
        error:      Human-readable error message on failure.
        dry_run:    ``True`` when the post was generated but not sent because
                    ``ENABLE_POSTING=false``.  ``success`` will also be ``True``
                    in this case.
    """

    platform: str
    success: bool
    post_id: str | None = None
    url: str | None = None
    error: str | None = None
    dry_run: bool = False


__all__ = [
    "FeedSource",
    "Article",
    "ArticleSummary",
    "ContentPackage",
    "PublishResult",
]
