"""
tests/test_config.py
====================
Unit tests for agent/config.py.

TODO:
    - Test that AgentConfig reads values from environment variables.
    - Test that default values are applied when env vars are absent.
    - Test that secret names are never overridden by environment variables.
"""

import os

import pytest

from agent.config import AgentConfig


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_default_aws_region(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig should fall back to us-east-1 when AWS_REGION is not set."""
        monkeypatch.delenv("AWS_REGION", raising=False)
        # TODO: reload config after env change once config is refactored to a function
        assert AgentConfig.aws_region in (os.environ.get("AWS_REGION", "us-east-1"),)

    def test_secret_names_are_constants(self) -> None:
        """Secret Manager names must be defined as constants and never be empty."""
        assert AgentConfig.LINKEDIN_SECRET_NAME
        assert AgentConfig.NEWS_API_SECRET_NAME

    # TODO: add tests for bedrock_model_id, dynamodb_table_name, log_level defaults
