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


class AgentConfig:
    """
    Holds all runtime configuration for the agent.

    Attributes:
        aws_region: AWS region used for all SDK calls.
        bedrock_model_id: Amazon Bedrock model ID used for summarisation and post generation.
        dynamodb_table_name: DynamoDB table that tracks processed article URLs.
        log_level: Logging verbosity (default: INFO).
        enabled_publishers: Ordered list of platform keys to publish to.
        blog_output_path: Local directory where BlogPublisher writes Markdown files.

    TODO:
        - Add news source URLs / RSS feed list.
        - Add configurable scheduling parameters.
    """

    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")
    bedrock_model_id: str = os.environ.get(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    dynamodb_table_name: str = os.environ.get("DYNAMODB_TABLE_NAME", "tech-news-agent-articles")
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")

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
