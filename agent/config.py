"""
agent/config.py
===============
Centralised configuration for the tech-news-agent.

All non-sensitive configuration values are read from environment variables.
Sensitive values (API keys, credentials) are fetched at runtime from
AWS Secrets Manager — never stored here or in any committed file.

Publisher selection
-------------------
Set ``ENABLED_PUBLISHERS`` to a comma-separated list of platform keys to
control where the agent posts.  Valid keys: ``blog``, ``linkedin``,
``instagram``, ``youtube``.

Examples::

    ENABLED_PUBLISHERS=blog                   # default — no credentials needed
    ENABLED_PUBLISHERS=linkedin,instagram
    ENABLED_PUBLISHERS=blog,linkedin,youtube

News feed sources
-----------------
Feed URLs are resolved at runtime using a **hybrid** strategy:

1. The ``fetch_tech_news`` tool queries DynamoDB (``NEWS_FEEDS_TABLE``) for
   enabled feed records.  This allows feeds to be added or disabled at
   runtime without redeployment.
2. If the table is empty or unreachable the tool falls back to the
   comma-separated ``NEWS_FEED_URLS`` environment variable.
3. If that variable is also absent the hardcoded ``DEFAULT_NEWS_FEED_URLS``
   list is used.

DynamoDB feed record schema (partition key ``feed_url``)::

    {
        "feed_url":    "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "name":        "Ars Technica – Technology Lab",
        "category":    "general",
        "enabled":     true
    }

TODO:
    - Add helper to fetch secrets from AWS Secrets Manager.
    - Validate required environment variables on startup.
    - Add support for local overrides via a `.env.local` file (dev only).
"""

from __future__ import annotations

import os


def _parse_list(env_var: str, default: str) -> list[str]:
    """Parse a comma-separated environment variable into a stripped list."""
    raw = os.environ.get(env_var, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Hardcoded fallback RSS feeds used when DynamoDB and env var are both absent.
# These are well-known, stable tech news sources.
# ---------------------------------------------------------------------------
_DEFAULT_FEED_URLS = ",".join([
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    "https://aws.amazon.com/blogs/aws/feed/",
    "https://news.ycombinator.com/rss",
])


class AgentConfig:
    """
    Holds all runtime configuration for the agent.

    Attributes:
        aws_region: AWS region used for all SDK calls.
        bedrock_model_id: Amazon Bedrock model ID used for summarisation and post generation.
        dynamodb_table_name: DynamoDB table that tracks processed article URLs.
        news_feeds_table: DynamoDB table that stores the managed feed registry.
        news_feed_urls: Fallback list of RSS feed URLs (env var or hardcoded defaults).
        max_articles_per_run: Maximum articles to process in a single pipeline run.
        log_level: Logging verbosity (default: INFO).
        enabled_publishers: Ordered list of platform keys to publish to.
        blog_output_path: Local directory where BlogPublisher writes Markdown files.
    """

    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.environ.get(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    dynamodb_table_name: str = os.environ.get("DYNAMODB_TABLE_NAME", "tech-news-agent-articles")
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")

    # -------------------------------------------------------------------------
    # News feed configuration
    # -------------------------------------------------------------------------
    #: DynamoDB table that stores the managed feed registry.
    #: Partition key: ``feed_url`` (String).
    news_feeds_table: str = os.environ.get("NEWS_FEEDS_TABLE", "tech-news-agent-feeds")

    #: Fallback RSS feed URLs used when DynamoDB is empty or unavailable.
    #: Override via NEWS_FEED_URLS env var (comma-separated).
    news_feed_urls: list[str] = _parse_list("NEWS_FEED_URLS", _DEFAULT_FEED_URLS)

    #: Maximum number of articles to process per pipeline run.
    #: Caps Bedrock token usage; raise if you need more coverage.
    max_articles_per_run: int = int(os.environ.get("MAX_ARTICLES_PER_RUN", "20"))

    #: How many days to retain processed article records in DynamoDB.
    #: After this period the TTL attribute causes DynamoDB to delete the item
    #: automatically, allowing the same URL to be re-processed if it resurfaces.
    article_ttl_days: int = int(os.environ.get("ARTICLE_TTL_DAYS", "90"))

    # -------------------------------------------------------------------------
    # Publisher configuration
    # -------------------------------------------------------------------------
    #: Comma-separated list of platform keys.  Default is "blog" which requires
    #: no external credentials and is safe to enable in all environments.
    enabled_publishers: list[str] = _parse_list("ENABLED_PUBLISHERS", "blog")

    #: Directory where BlogPublisher writes generated Markdown files.
    blog_output_path: str = os.environ.get("BLOG_OUTPUT_PATH", "output/posts")

    # -------------------------------------------------------------------------
    # AWS Secrets Manager secret names
    # Values are NEVER stored here — only the key names used to look them up.
    # -------------------------------------------------------------------------
    NEWS_API_SECRET_NAME: str = "tech-news-agent/news-api"
    LINKEDIN_SECRET_NAME: str = "tech-news-agent/linkedin"
    INSTAGRAM_SECRET_NAME: str = "tech-news-agent/instagram"
    YOUTUBE_SECRET_NAME: str = "tech-news-agent/youtube"
