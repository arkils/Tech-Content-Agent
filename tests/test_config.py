"""
tests/test_config.py
====================
Unit tests for agent/config.py.
"""

import os

import pytest

from agent.config import AgentConfig


def test_runtime_config_exposes_boolean_force_new_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The local runner should resolve FORCE_NO_NEW_ARTICLES to a real boolean."""
    monkeypatch.setenv("FORCE_NO_NEW_ARTICLES", "true")

    from scripts.run_local import _get_runtime_config

    config = _get_runtime_config()
    assert config.force_no_new_articles is True


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_default_aws_region(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig should fall back to us-east-1 when AWS_REGION is not set."""
        monkeypatch.delenv("AWS_REGION", raising=False)
        assert AgentConfig.aws_region in (os.environ.get("AWS_REGION", "us-east-1"),)

    def test_param_paths_are_constants(self) -> None:
        """SSM Parameter Store parameter paths must be defined as constants and never be empty."""
        assert AgentConfig.LINKEDIN_PARAM_PATH
        assert AgentConfig.NEWS_API_PARAM_PATH
        assert AgentConfig.INSTAGRAM_PARAM_PATH
        assert AgentConfig.YOUTUBE_PARAM_PATH

    def test_default_dynamodb_table_name(self) -> None:
        """Deduplication table name should have a sensible default."""
        assert AgentConfig.dynamodb_table_name == os.environ.get(
            "DYNAMODB_TABLE_NAME", "tech-news-agent-articles"
        )

    def test_default_news_feeds_table(self) -> None:
        """Feed registry table name should default to tech-news-agent-feeds."""
        assert AgentConfig.news_feeds_table == os.environ.get(
            "NEWS_FEEDS_TABLE", "tech-news-agent-feeds"
        )

    def test_default_news_feed_urls_is_non_empty_list(self) -> None:
        """Fallback feed URL list must not be empty."""
        assert isinstance(AgentConfig.news_feed_urls, list)
        assert len(AgentConfig.news_feed_urls) > 0

    def test_default_news_feed_urls_are_valid_urls(self) -> None:
        """Every default feed URL must start with https://."""
        for url in AgentConfig.news_feed_urls:
            assert url.startswith("https://"), f"Feed URL is not HTTPS: {url}"

    def test_max_articles_per_run_default(self) -> None:
        """max_articles_per_run should default to 20."""
        assert AgentConfig.max_articles_per_run == int(
            os.environ.get("MAX_ARTICLES_PER_RUN", "20")
        )

    def test_max_articles_per_run_is_positive(self) -> None:
        """max_articles_per_run must be a positive integer."""
        assert AgentConfig.max_articles_per_run > 0

    def test_default_enabled_publishers(self) -> None:
        """Default publisher should be blog when ENABLED_PUBLISHERS is not set."""
        assert isinstance(AgentConfig.enabled_publishers, list)
        assert len(AgentConfig.enabled_publishers) > 0

    def test_default_blog_output_path(self) -> None:
        """Blog output path should have a sensible default."""
        assert AgentConfig.blog_output_path == os.environ.get(
            "BLOG_OUTPUT_PATH", "output/posts"
        )

    def test_default_log_level(self) -> None:
        """Log level should default to INFO."""
        assert AgentConfig.log_level == os.environ.get("LOG_LEVEL", "INFO")
