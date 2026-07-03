"""
agent/publishers/__init__.py
=============================
Publisher registry and factory for tech-news-agent.

This module is the single place where platform publishers are registered.
Adding a new publisher requires only:
  1. Creating the publisher module in this package.
  2. Adding an entry to ``PUBLISHER_REGISTRY`` below.
  3. Updating ``AgentConfig`` with the platform's SSM Parameter Store path.

Supported platforms
-------------------
+-------------+---------------------+----------------------------------+
| Key         | Class               | Notes                            |
+=============+=====================+==================================+
| blog        | BlogPublisher       | Default — no credentials needed  |
| linkedin    | LinkedInPublisher   | LinkedIn Share API               |
| instagram   | InstagramPublisher  | Meta Graph API                   |
| youtube     | YouTubePublisher    | YouTube Data API v3              |
+-------------+---------------------+----------------------------------+

Usage::

    from agent.publishers import get_active_publishers
    from agent.config import AgentConfig

    publishers = get_active_publishers(AgentConfig.enabled_publishers)
    for publisher in publishers:
        result = publisher.run(content_package)

TODO:
    - Add a ``TikTokPublisher`` once the TikTok for Developers API is stable.
    - Add a ``TwitterPublisher`` (X API v2).
    - Add a ``DevToPublisher`` (https://developers.forem.com/api).
    - Add a ``HashnodePublisher`` (https://apidocs.hashnode.com/).
"""

from __future__ import annotations

from agent.publishers.base import BasePublisher, ContentPackage, PublishResult
from agent.publishers.blog import BlogPublisher
from agent.publishers.instagram import InstagramPublisher
from agent.publishers.linkedin import LinkedInPublisher
from agent.publishers.youtube import YouTubePublisher

__all__ = [
    "PUBLISHER_REGISTRY",
    "BasePublisher",
    "BlogPublisher",
    "ContentPackage",
    "InstagramPublisher",
    "LinkedInPublisher",
    "PublishResult",
    "YouTubePublisher",
    "get_active_publishers",
]

# ---------------------------------------------------------------------------
# Registry — maps the string key used in config to the publisher class
# ---------------------------------------------------------------------------

PUBLISHER_REGISTRY: dict[str, type[BasePublisher]] = {
    "blog": BlogPublisher,
    "linkedin": LinkedInPublisher,
    "instagram": InstagramPublisher,
    "youtube": YouTubePublisher,
}


def get_active_publishers(enabled: list[str]) -> list[BasePublisher]:
    """
    Instantiate and return publishers for every enabled platform.

    Args:
        enabled: List of platform keys from ``AgentConfig.enabled_publishers``.
                 Example: ``["blog", "linkedin"]``

    Returns:
        List of instantiated ``BasePublisher`` objects, in the order given.

    Raises:
        ValueError: If any key in ``enabled`` is not registered.

    Example::

        publishers = get_active_publishers(["blog", "linkedin"])
        # → [BlogPublisher(), LinkedInPublisher()]
    """
    publishers: list[BasePublisher] = []
    unknown = [k for k in enabled if k not in PUBLISHER_REGISTRY]
    if unknown:
        raise ValueError(
            f"Unknown publisher(s): {unknown}. "
            f"Registered platforms: {sorted(PUBLISHER_REGISTRY)}"
        )
    for key in enabled:
        publishers.append(PUBLISHER_REGISTRY[key]())
    return publishers
