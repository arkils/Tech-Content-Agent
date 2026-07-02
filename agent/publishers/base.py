"""
agent/publishers/base.py
========================
Abstract base class and shared data contracts for all content publishers.

A publisher is responsible for two things:
  1. Formatting a platform-agnostic ContentPackage into platform-specific text.
  2. Delivering that text to the target platform (API call, file write, etc.).

To add a new platform:
  1. Create a new module in this package (e.g. ``tiktok.py``).
  2. Subclass ``BasePublisher`` and implement ``format_content`` and ``publish``.
  3. Register the class in ``agent/publishers/__init__.py``.
  4. Add a Secrets Manager entry for any required credentials.
  5. Add a platform prompt in ``agent/prompts/platforms/``.

Data contracts (``ArticleSummary``, ``ContentPackage``, ``PublishResult``) are
defined in ``agent/models`` and re-exported here for backwards compatibility.

TODO:
    - Add retry logic with exponential back-off to ``run()``.
    - Emit CloudWatch metrics per publisher on success / failure.
    - Add an async variant for parallel multi-platform publishing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from agent.models import ArticleSummary, ContentPackage, PublishResult

logger = logging.getLogger(__name__)

# Re-export so existing imports of these names from this module keep working.
__all__ = ["ArticleSummary", "ContentPackage", "PublishResult", "BasePublisher"]


class BasePublisher(ABC):
    """
    Abstract base class for all content publishers.

    Subclasses must set ``platform_name`` and implement:
      - ``format_content(package)`` → platform-specific string
      - ``publish(content)``        → ``PublishResult``

    Callers should invoke ``run(package)`` which orchestrates both steps and
    handles logging.

    TODO:
        - Add ``validate_credentials()`` abstract method called on startup.
        - Add ``dry_run`` flag to format without publishing.
    """

    #: Override in each subclass with the platform's string key.
    platform_name: str = "unknown"

    @abstractmethod
    def format_content(self, package: ContentPackage) -> str:
        """
        Transform a ContentPackage into platform-appropriate text.

        Args:
            package: The platform-agnostic content package from the pipeline.

        Returns:
            Formatted string ready to be posted to the target platform.
        """

    @abstractmethod
    def publish(self, content: str) -> PublishResult:
        """
        Deliver the formatted content to the target platform.

        Args:
            content: Platform-formatted content string from ``format_content``.

        Returns:
            ``PublishResult`` describing the outcome.
        """

    def run(self, package: ContentPackage) -> PublishResult:
        """
        Orchestrate ``format_content → publish`` for this publisher.

        Subclasses must not override this method.  Override
        ``format_content`` and ``publish`` instead.
        """
        logger.info("Starting publish run for platform=%s", self.platform_name)
        try:
            content = self.format_content(package)
            result = self.publish(content)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error publishing to %s", self.platform_name)
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error=str(exc),
            )

        if result.success:
            logger.info(
                "Published successfully to %s post_id=%s url=%s",
                self.platform_name,
                result.post_id,
                result.url,
            )
        else:
            logger.error(
                "Publish failed for %s: %s",
                self.platform_name,
                result.error,
            )
        return result
