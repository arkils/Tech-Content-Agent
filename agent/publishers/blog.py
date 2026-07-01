"""
agent/publishers/blog.py
========================
Blog / local file publisher.

Writes a formatted Markdown blog post to a configured output path.
This is the **default** publisher — it requires no external credentials
and is suitable for local development, testing, and initial deployment.

In a production setup the generated Markdown file can be:
  - Committed to a GitHub Pages / Hugo / Docusaurus repository.
  - Uploaded to an S3 bucket fronted by CloudFront.
  - Pushed to a Hashnode / Dev.to / Substack API.

Output path is controlled by ``AgentConfig.BLOG_OUTPUT_PATH``.

TODO:
    - Add an S3 upload variant (upload Markdown to a configured bucket).
    - Add a Hashnode API variant (https://apidocs.hashnode.com/).
    - Add a Dev.to API variant (https://developers.forem.com/api).
    - Add front-matter metadata (date, tags, author, canonical URL).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

logger = logging.getLogger(__name__)


class BlogPublisher(BasePublisher):
    """
    Writes a Markdown blog post to the local filesystem.

    This publisher is the default and requires no external credentials.
    It is always safe to enable for smoke-testing the pipeline.

    Args:
        output_dir: Directory where generated Markdown files are written.
                    Defaults to ``AgentConfig.BLOG_OUTPUT_PATH``.

    TODO:
        - Accept an injected filesystem abstraction for testability.
        - Add configurable template for the Markdown front-matter block.
    """

    platform_name = "blog"

    def __init__(self, output_dir: str | None = None) -> None:
        from agent.config import AgentConfig  # local import avoids circular dep

        self._output_dir = Path(output_dir or AgentConfig.blog_output_path)

    def format_content(self, package: ContentPackage) -> str:
        """
        Format a ContentPackage as a Markdown blog post with front-matter.

        TODO:
            - Call Bedrock with ``agent/prompts/platforms/blog.md`` for a
              longer, richer blog-style post instead of using ``raw_post``.
            - Generate a slug from the topic for the filename.
        """
        now = datetime.now(UTC)
        tags = ", ".join(f'"{k}"' for k in package.keywords[:8])
        sources = "\n".join(
            f"- [{a.title}]({a.url}) — {a.source}" for a in package.articles
        )

        return f"""---
title: "{package.topic}"
date: "{now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
tags: [{tags}]
draft: false
---

{package.digest}

{package.raw_post}

## Sources

{sources}
"""

    def publish(self, content: str) -> PublishResult:
        """
        Write the formatted Markdown to ``output_dir``.

        The filename is ``<ISO-date>-<uuid4-short>.md`` to guarantee
        uniqueness across runs.
        """
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            short_id = str(uuid.uuid4())[:8]
            filename = f"{datetime.now(UTC).strftime('%Y-%m-%d')}-{short_id}.md"
            output_path = self._output_dir / filename
            output_path.write_text(content, encoding="utf-8")
            logger.info("Blog post written to %s", output_path)
            return PublishResult(
                platform=self.platform_name,
                success=True,
                url=str(output_path),
            )
        except OSError as exc:
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error=str(exc),
            )
