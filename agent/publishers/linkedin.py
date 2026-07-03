"""
agent/publishers/linkedin.py
=============================
LinkedIn content publisher.

Formats a ContentPackage as a professional LinkedIn post and delivers it
via the LinkedIn Share API.

Credentials are fetched from AWS SSM Parameter Store at publish time.
Parameter path: ``AgentConfig.LINKEDIN_PARAM_PATH``.

Expected secret JSON structure::

    {
        "access_token": "<oauth2-access-token>",
        "author_urn":   "urn:li:person:<person-id>"
    }

LinkedIn API reference:
    https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

TODO:
    - Implement ``_get_credentials()`` using boto3 Secrets Manager.
    - Implement ``publish()`` using the LinkedIn Share API (``/rest/posts``).
    - Add token refresh logic (LinkedIn OAuth2 tokens expire after 60 days).
    - Enforce LinkedIn's character limit (3,000 chars for regular posts).
    - Add image attachment support.
"""

from __future__ import annotations

import logging

from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

logger = logging.getLogger(__name__)

# LinkedIn recommends posts between 150–300 words for optimal reach
_MAX_CHARS = 3_000


class LinkedInPublisher(BasePublisher):
    """
    Publishes formatted tech-news content to LinkedIn.

    TODO:
        - Inject a boto3 Secrets Manager client via the constructor for testability.
        - Add a ``dry_run`` flag that logs the post without calling the API.
    """

    platform_name = "linkedin"

    def format_content(self, package: ContentPackage) -> str:
        """
        Format a ContentPackage as a LinkedIn post.

        Uses the pre-generated ``raw_post`` from the pipeline.  In a future
        iteration this will call Bedrock with the LinkedIn-specific prompt
        to refine the text for the platform's audience and character limits.

        TODO:
            - Call Bedrock with ``agent/prompts/platforms/linkedin.md``.
            - Append relevant hashtags derived from ``package.keywords``.
            - Truncate gracefully if the generated text exceeds ``_MAX_CHARS``.
        """
        hashtags = " ".join(f"#{kw.replace(' ', '')}" for kw in package.keywords[:5])
        post = f"{package.raw_post}\n\n{hashtags}".strip()
        if len(post) > _MAX_CHARS:
            post = post[:_MAX_CHARS - 3] + "..."
        return post

    def publish(self, content: str) -> PublishResult:
        """
        Deliver content to LinkedIn via the Share API.

        TODO:
            - Retrieve credentials from AWS Secrets Manager.
            - POST to ``https://api.linkedin.com/rest/posts``.
            - Parse the response and return ``post_id`` and ``url``.
        """
        logger.info(
            "LinkedIn publisher is a placeholder. Content preview:\n%s",
            content[:200],
        )
        # TODO: implement real API call
        raise NotImplementedError("LinkedInPublisher.publish() is not yet implemented")
