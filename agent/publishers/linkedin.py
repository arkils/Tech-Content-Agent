"""
agent/publishers/linkedin.py
=============================
LinkedIn content publisher.

Formats a ContentPackage as a professional LinkedIn post and delivers it
via the LinkedIn Share API (``/rest/posts``).

Credentials are fetched from AWS SSM Parameter Store at publish time.
Parameter path: ``AgentConfig.LINKEDIN_PARAM_PATH``.

Expected parameter JSON structure::

    {
        "access_token": "<oauth2-access-token>",
        "author_urn":   "urn:li:person:<person-id>"
    }

LinkedIn API reference:
    https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

Note:
    LinkedIn OAuth2 tokens expire after 60 days.  Update the SSM parameter
    before expiry to avoid publish failures.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import boto3
import requests

from agent.config import AgentConfig
from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

if TYPE_CHECKING:
    from mypy_boto3_ssm import SSMClient

logger = logging.getLogger(__name__)

# LinkedIn recommends posts between 150–300 words for optimal reach
_MAX_CHARS = 3_000
_LINKEDIN_API_URL = "https://api.linkedin.com/rest/posts"
_LINKEDIN_API_VERSION = "202504"


class LinkedInPublisher(BasePublisher):
    """
    Publishes formatted tech-news content to LinkedIn.

    Args:
        ssm_client: An optional pre-built ``boto3`` SSM client.
            Inject in tests to avoid real AWS calls.  Defaults to a new
            client using ``AgentConfig.aws_region``.
        dry_run: When ``True``, log the post instead of calling the LinkedIn API.
            Defaults to ``not AgentConfig.enable_posting``, so posting is off
            until ``ENABLE_POSTING=true`` is set in the Lambda environment.
    """

    platform_name = "linkedin"

    def __init__(self, ssm_client: Any | None = None, dry_run: bool | None = None) -> None:
        self._ssm_client = ssm_client or boto3.client(
            "ssm", region_name=AgentConfig.aws_region
        )
        self._dry_run = (not AgentConfig.enable_posting) if dry_run is None else dry_run

    def format_content(self, package: ContentPackage) -> str:
        """
        Format a ContentPackage as a LinkedIn post.

        Uses the pre-generated ``raw_post`` from the pipeline, appends
        up to five keyword-derived hashtags, and truncates to ``_MAX_CHARS``.
        """
        hashtags = " ".join(f"#{kw.replace(' ', '')}" for kw in package.keywords[:5])
        post = f"{package.raw_post}\n\n{hashtags}".strip()
        if len(post) > _MAX_CHARS:
            post = post[:_MAX_CHARS - 3] + "..."
        return post

    def _get_credentials(self) -> dict[str, str]:
        """Fetch LinkedIn credentials from AWS SSM Parameter Store.

        Returns:
            A dict with ``access_token`` and ``author_urn``.

        Raises:
            KeyError: If required keys are missing from the parameter.
            Exception: On any SSM error.
        """
        response = self._ssm_client.get_parameter(
            Name=AgentConfig.LINKEDIN_PARAM_PATH, WithDecryption=True
        )
        creds: dict[str, str] = json.loads(response["Parameter"]["Value"])
        if "access_token" not in creds or "author_urn" not in creds:
            raise KeyError(
                f"LinkedIn parameter at '{AgentConfig.LINKEDIN_PARAM_PATH}' must contain "
                "'access_token' and 'author_urn'."
            )
        return creds

    def publish(self, content: str) -> PublishResult:
        """
        Deliver content to LinkedIn via the Share API.

        Args:
            content: The formatted post text from ``format_content``.

        Returns:
            ``PublishResult`` with ``success=True`` and ``post_id`` on success,
            or ``success=False`` and ``error`` on failure.
        """
        if self._dry_run:
            logger.info(
                "[DRY RUN] ENABLE_POSTING is false — post NOT sent to LinkedIn.\n"
                "Formatted post:\n%s",
                content,
            )
            return PublishResult(
                platform=self.platform_name, success=True, post_id="dry-run", dry_run=True
            )

        try:
            creds = self._get_credentials()
        except Exception:
            logger.exception("Failed to retrieve LinkedIn credentials from SSM Parameter Store")
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error="Failed to retrieve credentials from SSM Parameter Store.",
            )

        headers = {
            "Authorization": f"Bearer {creds['access_token']}",
            "Content-Type": "application/json",
            "LinkedIn-Version": _LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }
        payload = {
            "author": creds["author_urn"],
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        try:
            response = requests.post(
                _LINKEDIN_API_URL,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error(
                "LinkedIn API returned %s: %s",
                exc.response.status_code,
                exc.response.text,
            )
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error=f"LinkedIn API error {exc.response.status_code}: {exc.response.text}",
            )
        except requests.RequestException as exc:
            logger.exception("LinkedIn API request failed")
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error=f"Request failed: {exc}",
            )

        # LinkedIn returns the new post URN in the X-RestLi-Id header (201 Created)
        post_id = response.headers.get("X-RestLi-Id") or response.headers.get("x-restli-id")
        logger.info("Published LinkedIn post — post_id=%s", post_id)
        return PublishResult(
            platform=self.platform_name,
            success=True,
            post_id=post_id,
        )
