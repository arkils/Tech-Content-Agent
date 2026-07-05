"""
tests/publishers/test_linkedin.py
===================================
Unit tests for agent/publishers/linkedin.py.

AWS calls are mocked with moto; HTTP calls to the LinkedIn API are mocked
with unittest.mock.patch so no real network traffic is generated.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import boto3
import moto
import pytest
import requests

from agent.config import AgentConfig
from agent.publishers.base import ArticleSummary, ContentPackage, PublishResult
from agent.publishers.linkedin import LinkedInPublisher, _MAX_CHARS


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def package() -> ContentPackage:
    return ContentPackage(
        topic="Top Tech News",
        digest="Brief digest of this week's tech news.",
        articles=[
            ArticleSummary(
                title="Something Big Happened",
                url="https://techcrunch.com/something-big",
                summary="A major announcement was made.",
                relevance_score=5,
                source="TechCrunch",
            ),
        ],
        keywords=["aws", "ai", "cloud", "python", "devops"],
        raw_post="This week in tech: exciting things happened across AI, cloud, and open-source.",
    )


@pytest.fixture
def ssm_client():
    """A moto-backed SSM client pre-loaded with LinkedIn credentials."""
    with moto.mock_aws():
        client = boto3.client("ssm", region_name="us-east-1")
        client.put_parameter(
            Name=AgentConfig.LINKEDIN_PARAM_PATH,
            Value=json.dumps(
                {
                    "access_token": "test-access-token",
                    "author_urn": "urn:li:person:test123",
                }
            ),
            Type="SecureString",
        )
        yield client


# ---------------------------------------------------------------------------
# format_content tests
# ---------------------------------------------------------------------------


class TestLinkedInPublisherFormatContent:
    def test_returns_non_empty_string(self, package: ContentPackage) -> None:
        result = LinkedInPublisher().format_content(package)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_raw_post(self, package: ContentPackage) -> None:
        result = LinkedInPublisher().format_content(package)
        assert package.raw_post in result

    def test_includes_hashtags(self, package: ContentPackage) -> None:
        result = LinkedInPublisher().format_content(package)
        assert "#aws" in result

    def test_does_not_exceed_max_chars(self, package: ContentPackage) -> None:
        long_package = ContentPackage(
            topic=package.topic,
            digest=package.digest,
            articles=package.articles,
            keywords=package.keywords,
            raw_post="A" * (_MAX_CHARS + 500),
        )
        result = LinkedInPublisher().format_content(long_package)
        assert len(result) <= _MAX_CHARS

    def test_truncated_post_ends_with_ellipsis(self, package: ContentPackage) -> None:
        long_package = ContentPackage(
            topic=package.topic,
            digest=package.digest,
            articles=package.articles,
            keywords=package.keywords,
            raw_post="B" * (_MAX_CHARS + 500),
        )
        result = LinkedInPublisher().format_content(long_package)
        assert result.endswith("...")


# ---------------------------------------------------------------------------
# _get_credentials tests
# ---------------------------------------------------------------------------


class TestLinkedInPublisherGetCredentials:
    def test_returns_access_token_and_author_urn(self, ssm_client) -> None:
        publisher = LinkedInPublisher(ssm_client=ssm_client)
        creds = publisher._get_credentials()
        assert creds["access_token"] == "test-access-token"
        assert creds["author_urn"] == "urn:li:person:test123"

    def test_raises_key_error_when_secret_is_incomplete(self, ssm_client) -> None:
        ssm_client.put_parameter(
            Name=AgentConfig.LINKEDIN_PARAM_PATH,
            Value=json.dumps({"access_token": "only-token"}),
            Type="SecureString",
            Overwrite=True,
        )
        publisher = LinkedInPublisher(ssm_client=ssm_client)
        with pytest.raises(KeyError, match="author_urn"):
            publisher._get_credentials()


# ---------------------------------------------------------------------------
# publish() tests
# ---------------------------------------------------------------------------


class TestLinkedInPublisherPublish:
    def test_publish_success_returns_publish_result(self, ssm_client) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"X-RestLi-Id": "urn:li:share:9999"}
        mock_response.raise_for_status = MagicMock()

        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=False)

        with patch("agent.publishers.linkedin.requests.post", return_value=mock_response):
            result = publisher.publish("Test LinkedIn post content.")

        assert isinstance(result, PublishResult)
        assert result.success is True
        assert result.platform == "linkedin"
        assert result.post_id == "urn:li:share:9999"
        assert result.error is None

    def test_publish_sends_correct_payload(self, ssm_client) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"X-RestLi-Id": "urn:li:share:1234"}
        mock_response.raise_for_status = MagicMock()

        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=False)

        with patch("agent.publishers.linkedin.requests.post", return_value=mock_response) as mock_post:
            publisher.publish("Post body text.")

        _, call_kwargs = mock_post.call_args
        payload = call_kwargs["json"]
        assert payload["author"] == "urn:li:person:test123"
        assert payload["commentary"] == "Post body text."
        assert payload["visibility"] == "PUBLIC"
        assert payload["lifecycleState"] == "PUBLISHED"

    def test_publish_sends_bearer_token_header(self, ssm_client) -> None:
        mock_response = MagicMock()
        mock_response.headers = {}
        mock_response.raise_for_status = MagicMock()

        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=False)

        with patch("agent.publishers.linkedin.requests.post", return_value=mock_response) as mock_post:
            publisher.publish("Post body text.")

        _, call_kwargs = mock_post.call_args
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-access-token"
        assert call_kwargs["headers"]["LinkedIn-Version"] == "202506"

    def test_publish_returns_failure_on_http_error(self, ssm_client) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        http_error = requests.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=False)

        with patch("agent.publishers.linkedin.requests.post", return_value=mock_response):
            result = publisher.publish("Post body.")

        assert result.success is False
        assert result.platform == "linkedin"
        assert "403" in result.error

    def test_publish_returns_failure_on_request_exception(self, ssm_client) -> None:
        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=False)

        with patch(
            "agent.publishers.linkedin.requests.post",
            side_effect=requests.ConnectionError("timeout"),
        ):
            result = publisher.publish("Post body.")

        assert result.success is False
        assert result.error is not None

    def test_publish_returns_failure_when_credentials_missing(self) -> None:
        with moto.mock_aws():
            empty_client = boto3.client("ssm", region_name="us-east-1")
            publisher = LinkedInPublisher(ssm_client=empty_client, dry_run=False)
            result = publisher.publish("Post body.")

        assert result.success is False
        assert result.platform == "linkedin"
        assert result.error is not None


# ---------------------------------------------------------------------------
# dry_run tests
# ---------------------------------------------------------------------------


class TestLinkedInPublisherDryRun:
    def test_dry_run_returns_success_without_calling_api(self, ssm_client) -> None:
        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=True)

        with patch("agent.publishers.linkedin.requests.post") as mock_post:
            result = publisher.publish("Post body.")

        mock_post.assert_not_called()
        assert result.success is True
        assert result.post_id == "dry-run"
        assert result.platform == "linkedin"

    def test_dry_run_does_not_fetch_credentials(self) -> None:
        # dry_run=True should return before ever touching SSM Parameter Store
        with moto.mock_aws():
            empty_client = boto3.client("ssm", region_name="us-east-1")
            publisher = LinkedInPublisher(ssm_client=empty_client, dry_run=True)
            result = publisher.publish("Post body.")

        assert result.success is True
        assert result.post_id == "dry-run"

    def test_dry_run_false_calls_api(self, ssm_client) -> None:
        mock_response = MagicMock()
        mock_response.headers = {"X-RestLi-Id": "urn:li:share:1"}
        mock_response.raise_for_status = MagicMock()

        publisher = LinkedInPublisher(ssm_client=ssm_client, dry_run=False)

        with patch("agent.publishers.linkedin.requests.post", return_value=mock_response) as mock_post:
            result = publisher.publish("Post body.")

        mock_post.assert_called_once()
        assert result.success is True
