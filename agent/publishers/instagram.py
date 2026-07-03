"""
agent/publishers/instagram.py
==============================
Instagram content publisher.

Formats a ContentPackage as an Instagram caption and publishes it via the
Instagram Graph API (Meta).

Credentials are fetched from AWS SSM Parameter Store at publish time.
Parameter path: ``AgentConfig.INSTAGRAM_PARAM_PATH``.

Expected secret JSON structure::

    {
        "access_token":  "<long-lived-user-access-token>",
        "instagram_account_id": "<ig-user-id>"
    }

Instagram Graph API reference:
    https://developers.facebook.com/docs/instagram-api/guides/content-publishing

Notes:
    - Instagram captions support up to 2,200 characters.
    - Only the first 125 characters are shown before the "more" fold.
    - Hashtags (up to 30) and @mentions are supported.
    - A media object (image or Reel cover) is required for feed posts.

TODO:
    - Implement ``_get_credentials()`` using boto3 Secrets Manager.
    - Implement ``publish()`` using the two-step Graph API flow:
        1. POST /ig-user-id/media  (create media container)
        2. POST /ig-user-id/media_publish  (publish container)
    - Add image generation or selection logic for the required visual.
    - Handle token refresh (long-lived tokens expire after 60 days).
"""

from __future__ import annotations

import logging

from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

logger = logging.getLogger(__name__)

_MAX_CAPTION_CHARS = 2_200
_MAX_HASHTAGS = 30


class InstagramPublisher(BasePublisher):
    """
    Publishes formatted tech-news content to Instagram.

    TODO:
        - Inject boto3 Secrets Manager client for testability.
        - Add image URL / asset support (required by the Graph API).
    """

    platform_name = "instagram"

    def format_content(self, package: ContentPackage) -> str:
        """
        Format a ContentPackage as an Instagram caption.

        Instagram favours shorter, punchy hooks in the first 125 characters
        followed by the main content.  Hashtags perform best at the end.

        TODO:
            - Call Bedrock with ``agent/prompts/platforms/instagram.md``.
            - Ensure first 125 characters are a compelling hook.
            - Append up to 30 relevant hashtags from ``package.keywords``.
        """
        hashtags = " ".join(
            f"#{kw.replace(' ', '')}" for kw in package.keywords[:_MAX_HASHTAGS]
        )
        caption = f"{package.raw_post}\n\n.\n.\n.\n{hashtags}".strip()
        if len(caption) > _MAX_CAPTION_CHARS:
            caption = caption[:_MAX_CAPTION_CHARS - 3] + "..."
        return caption

    def publish(self, content: str) -> PublishResult:
        """
        Publish to Instagram via the Graph API two-step flow.

        TODO:
            - Retrieve credentials from AWS Secrets Manager.
            - Select or generate an image asset for the post.
            - Step 1: Create media container via POST /ig-user-id/media.
            - Step 2: Publish container via POST /ig-user-id/media_publish.
        """
        logger.info(
            "Instagram publisher is a placeholder. Caption preview:\n%s",
            content[:200],
        )
        # TODO: implement real API call
        raise NotImplementedError("InstagramPublisher.publish() is not yet implemented")
