"""
tests/conftest.py
=================
Shared pytest fixtures for the tech-news-agent test suite.

TODO:
    - Add a fixture that starts a moto mock context for AWS services.
    - Add a fixture that provides a populated AgentConfig for tests.
    - Add a fixture that seeds the mock DynamoDB table with sample data.
"""

import pytest


@pytest.fixture
def sample_article() -> dict:
    """
    Returns a minimal article dict for use in unit tests.

    TODO: Expand once the Article model is defined.
    """
    return {
        "title": "Sample Tech Article",
        "url": "https://example.com/sample-article",
        "source": "Example Tech News",
        "published_at": "2026-01-01T00:00:00Z",
        "content": "This is a placeholder article body for testing purposes.",
    }
