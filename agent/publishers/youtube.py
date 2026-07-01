"""
agent/publishers/youtube.py
============================
YouTube Community Post publisher.

Formats a ContentPackage as a YouTube Community Post and delivers it via
the YouTube Data API v3.

Credentials are fetched from AWS Secrets Manager at publish time.
Secret name: configured via ``AgentConfig.YOUTUBE_SECRET_NAME``.

Expected secret JSON structure::

    {
        "client_id":     "<oauth2-client-id>",
        "client_secret": "<oauth2-client-secret>",
        "refresh_token": "<oauth2-refresh-token>",
        "channel_id":    "<youtube-channel-id>"
    }

YouTube Data API reference:
    https://developers.google.com/youtube/v3/docs/posts/insert

Notes:
    - Community Posts require a YouTube channel with Community tab enabled
      (typically available to channels with 500+ subscribers).
    - Community Post text limit: 5,000 characters.
    - Supports text, images, polls, and video links.
    - This publisher targets text + link posts initially.

TODO:
    - Implement ``_get_credentials()`` using boto3 Secrets Manager.
    - Implement OAuth2 token refresh using the stored refresh_token.
    - Implement ``publish()`` using the YouTube Data API v3 posts.insert.
    - Add optional video description variant for video uploads.
"""

from __future__ import annotations

import logging

from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

logger = logging.getLogger(__name__)

_MAX_POST_CHARS = 5_000


class YouTubePublisher(BasePublisher):
    """
    Publishes formatted tech-news content as a YouTube Community Post.

    TODO:
        - Inject boto3 Secrets Manager client for testability.
        - Add Google API client dependency (``google-api-python-client``).
    """

    platform_name = "youtube"

    def format_content(self, package: ContentPackage) -> str:
        """
        Format a ContentPackage as a YouTube Community Post.

        YouTube Community Posts work best with a strong opening sentence,
        a concise news digest, and links to source articles.

        TODO:
            - Call Bedrock with ``agent/prompts/platforms/youtube.md``.
            - Append top article URLs as a "Read more" list.
        """
        source_links = "\n".join(
            f"▶ {a.title}: {a.url}" for a in package.articles[:3]
        )
        post = f"{package.raw_post}\n\n{source_links}".strip()
        if len(post) > _MAX_POST_CHARS:
            post = post[:_MAX_POST_CHARS - 3] + "..."
        return post

    def publish(self, content: str) -> PublishResult:
        """
        Create a YouTube Community Post via the Data API v3.

        TODO:
            - Retrieve credentials from AWS Secrets Manager.
            - Refresh OAuth2 access token using the stored refresh_token.
            - POST to ``https://www.googleapis.com/youtube/v3/posts``.
        """
        logger.info(
            "YouTube publisher is a placeholder. Post preview:\n%s",
            content[:200],
        )
        # TODO: implement real API call
        raise NotImplementedError("YouTubePublisher.publish() is not yet implemented")
