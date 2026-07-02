"""
agent/tools/post_generator.py
==============================
``generate_post`` tool — per-platform Bedrock post generation.

Reads a platform-specific prompt template, renders it with the article
summaries, calls Amazon Bedrock, and returns a populated ``ContentPackage``
ready for the publisher layer.

Supported platforms (Phase 2)
------------------------------
- ``linkedin`` — professional post, 150–300 words, hashtags, no bullet points

Other platforms (blog, instagram, youtube) will be added in Phase 4 once
their ``publish()`` implementations are complete.

Prompt template location
------------------------
``agent/prompts/platforms/<platform>.md``

The template must contain at minimum the placeholders:
``{{TOPIC}}``, ``{{SUMMARIES}}``, ``{{KEYWORDS}}``.

Usage::

    import boto3
    from agent.tools.post_generator import PostGenerator

    generator = PostGenerator(bedrock_client=boto3.client("bedrock-runtime"))
    package = generator.run(summaries, platform="linkedin")
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from agent.config import AgentConfig
from agent.models import ArticleSummary, ContentPackage

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "platforms"

_SUPPORTED_PLATFORMS: frozenset[str] = frozenset({"linkedin"})


class PostGenerator:
    """
    Generates a platform-specific post using Amazon Bedrock.

    Inject a ``boto3.client("bedrock-runtime")`` instance so tests can
    mock the client without patching module globals.

    Args:
        bedrock_client: A ``boto3.client("bedrock-runtime")`` instance.
        config:         Agent configuration; defaults to ``AgentConfig``.
        prompts_dir:    Directory containing platform prompt templates.
    """

    def __init__(
        self,
        bedrock_client: object,
        config: type[AgentConfig] = AgentConfig,
        prompts_dir: Path = _PROMPTS_DIR,
    ) -> None:
        self._bedrock = bedrock_client
        self._config = config
        self._prompts_dir = prompts_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, summaries: list[ArticleSummary], platform: str = "linkedin") -> ContentPackage:
        """
        Generate a post for the given platform and return a ContentPackage.

        Args:
            summaries: Bedrock-summarised articles from ``summarise_articles``.
            platform:  Target platform key. Must be one of the supported platforms.

        Returns:
            A ``ContentPackage`` with ``topic``, ``digest``, ``articles``,
            ``keywords``, and ``raw_post`` populated.

        Raises:
            ValueError: If ``platform`` is not in the supported set.
            ValueError: If ``summaries`` is empty.
        """
        if platform not in _SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Platform '{platform}' is not supported by PostGenerator. "
                f"Supported: {sorted(_SUPPORTED_PLATFORMS)}"
            )
        if not summaries:
            raise ValueError("Cannot generate a post from an empty summaries list.")

        topic = _derive_topic(summaries)
        keywords = _derive_keywords(summaries)
        digest = _derive_digest(summaries)

        prompt = self._build_prompt(platform, topic, summaries, keywords)
        raw_post = self._call_bedrock(prompt)

        logger.info("Generated %s post (%d chars)", platform, len(raw_post))

        return ContentPackage(
            topic=topic,
            digest=digest,
            articles=summaries,
            keywords=keywords,
            raw_post=raw_post,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        platform: str,
        topic: str,
        summaries: list[ArticleSummary],
        keywords: list[str],
    ) -> str:
        """Load the platform prompt template and render it."""
        template_path = self._prompts_dir / f"{platform}.md"
        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template not found for platform '{platform}': {template_path}"
            )

        template = template_path.read_text(encoding="utf-8")

        # Extract only the fenced prompt block if the file uses a markdown code fence
        prompt_text = _extract_prompt_block(template)

        summaries_text = _serialise_summaries(summaries)
        keywords_text = ", ".join(keywords) if keywords else "technology, AI, software"

        return (
            prompt_text
            .replace("{{TOPIC}}", topic)
            .replace("{{SUMMARIES}}", summaries_text)
            .replace("{{KEYWORDS}}", keywords_text)
        )

    def _call_bedrock(self, prompt: str) -> str:
        """Call Bedrock ``converse`` and return the assistant message text."""
        response = self._bedrock.converse(
            modelId=self._config.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )

        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])

        for block in content:
            if block.get("text"):
                return block["text"].strip()

        raise RuntimeError(
            f"Bedrock converse returned no text content. Full response: {response}"
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _derive_topic(summaries: list[ArticleSummary]) -> str:
    """Return the title of the highest-relevance article as the topic."""
    top = max(summaries, key=lambda s: s.relevance_score)
    return top.title


def _derive_keywords(summaries: list[ArticleSummary]) -> list[str]:
    """
    Extract unique capitalised words from article titles as rough keywords.

    Filters out short common words and deduplicates.  Capped at 10 keywords.
    """
    stop_words = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for",
        "of", "is", "it", "its", "by", "as", "with", "this", "that",
        "new", "how", "why", "what", "will", "are", "was", "has", "be",
    }
    seen: set[str] = set()
    keywords: list[str] = []
    for summary in summaries:
        for word in summary.title.split():
            clean = re.sub(r"[^a-zA-Z]", "", word)
            lower = clean.lower()
            if len(clean) > 3 and lower not in stop_words and lower not in seen:
                seen.add(lower)
                keywords.append(clean)
    return keywords[:10]


def _derive_digest(summaries: list[ArticleSummary]) -> str:
    """Build a one-sentence digest from the top-scoring article summary."""
    top = max(summaries, key=lambda s: s.relevance_score)
    # Return just the first sentence of the summary
    sentences = top.summary.split(". ")
    return sentences[0] + ("." if not sentences[0].endswith(".") else "")


def _serialise_summaries(summaries: list[ArticleSummary]) -> str:
    """Render summaries as a numbered list for the prompt."""
    lines: list[str] = []
    for i, s in enumerate(summaries, start=1):
        lines.append(f"{i}. {s.title} (relevance: {s.relevance_score}/5)")
        lines.append(f"   {s.summary}")
        lines.append(f"   Source: {s.url}")
        lines.append("")
    return "\n".join(lines)


def _extract_prompt_block(template: str) -> str:
    """
    Extract the prompt text from inside a fenced code block if present.

    Platform prompt files use a markdown code fence to delimit the actual
    prompt text from surrounding documentation.  If no fence is found the
    whole file is used as-is.
    """
    match = re.search(r"```\s*\n(.*?)```", template, re.DOTALL)
    if match:
        return match.group(1).strip()
    return template.strip()
