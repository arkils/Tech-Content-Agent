"""
agent/tools/bedrock_summariser.py
==================================
``summarise_articles`` tool — Amazon Bedrock batch article summarisation.

Sends a batch of articles to Bedrock (Claude) using the prompt template at
``agent/prompts/summarize.md`` and parses the structured JSON response into
a list of ``ArticleSummary`` objects.

Bedrock API used
----------------
``bedrock-runtime`` ``converse`` — the modern multi-turn API that works
across all Claude model versions and handles content-type negotiation.

Response format expected from the model
----------------------------------------
The prompt instructs the model to return a JSON array.  Each element::

    {
        "title":        "Article headline",
        "url":          "https://example.com/article",
        "summary":      "2-3 sentence summary.",
        "relevance_score": 4,
        "duplicate_of": null          # or URL string if duplicate coverage
    }

Duplicate handling
------------------
Articles flagged by the model as ``duplicate_of`` another URL are dropped
from the returned list.  The caller receives only de-duplicated summaries.

Usage::

    import boto3
    from agent.tools.bedrock_summariser import ArticleSummariser

    summariser = ArticleSummariser(bedrock_client=boto3.client("bedrock-runtime"))
    summaries = summariser.run(articles)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from agent.config import AgentConfig
from agent.models import Article, ArticleSummary

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "summarize.md"


class ArticleSummariser:
    """
    Summarises a list of articles using Amazon Bedrock (Claude).

    Inject a ``boto3.client("bedrock-runtime")`` instance so tests can
    mock the client without patching module globals.

    Args:
        bedrock_client: A ``boto3.client("bedrock-runtime")`` instance.
        config:         Agent configuration; defaults to ``AgentConfig``.
        prompt_path:    Path to the summarise prompt template.  Defaults to
                        ``agent/prompts/summarize.md``.
    """

    def __init__(
        self,
        bedrock_client: object,
        config: type[AgentConfig] = AgentConfig,
        prompt_path: Path = _PROMPT_PATH,
    ) -> None:
        self._bedrock = bedrock_client
        self._config = config
        self._prompt_template = prompt_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, articles: list[Article]) -> list[ArticleSummary]:
        """
        Summarise a batch of articles using Bedrock.

        Args:
            articles: New (de-duplicated) articles from ``check_duplicate``.

        Returns:
            List of ``ArticleSummary`` objects, excluding any the model
            identified as duplicate coverage.
        """
        if not articles:
            logger.info("No articles to summarise")
            return []

        logger.info("Summarising %d article(s) with Bedrock", len(articles))
        prompt = self._build_prompt(articles)
        raw_response = self._call_bedrock(prompt)
        summaries = self._parse_response(raw_response)

        logger.info("Bedrock returned %d summary/summaries", len(summaries))
        return summaries

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(self, articles: list[Article]) -> str:
        """Render the prompt template with the serialised article batch."""
        articles_text = _serialise_articles(articles)
        return self._prompt_template.replace("{{ARTICLES}}", articles_text)

    def _call_bedrock(self, prompt: str) -> str:
        """
        Call Bedrock ``converse`` and return the assistant message text.

        Raises:
            RuntimeError: If the Bedrock response has no text content.
        """
        response = self._bedrock.converse(
            modelId=self._config.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
        )

        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])

        for block in content:
            if block.get("text"):
                return block["text"]

        raise RuntimeError(
            f"Bedrock converse returned no text content. Full response: {response}"
        )

    def _parse_response(self, raw: str) -> list[ArticleSummary]:
        """
        Parse the model's JSON response into ``ArticleSummary`` objects.

        The model is instructed to return a JSON array.  This method extracts
        the first JSON array found in the response (handles markdown fences),
        validates each item, and drops duplicate-flagged entries.

        Raises:
            ValueError: If no valid JSON array can be found in the response.
        """
        json_text = _extract_json_array(raw)

        try:
            items = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse Bedrock response as JSON: {exc}\nRaw: {raw}"
            ) from exc

        if not isinstance(items, list):
            raise ValueError(
                f"Expected a JSON array from Bedrock, got {type(items).__name__}. Raw: {raw}"
            )

        summaries: list[ArticleSummary] = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning("Skipping non-dict item in Bedrock response: %s", item)
                continue

            # Drop items the model flagged as duplicate coverage
            if item.get("duplicate_of"):
                logger.debug(
                    "Dropping duplicate article '%s' (duplicate of %s)",
                    item.get("title", "unknown"),
                    item["duplicate_of"],
                )
                continue

            title = item.get("title", "")
            url = item.get("url", "")
            summary = item.get("summary", "")
            relevance_score = item.get("relevance_score", 1)

            if not title or not url or not summary:
                logger.warning("Skipping incomplete summary item: %s", item)
                continue

            summaries.append(
                ArticleSummary(
                    title=title,
                    url=url,
                    summary=summary,
                    relevance_score=int(relevance_score),
                    source=item.get("source", ""),
                )
            )

        return summaries


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _serialise_articles(articles: list[Article]) -> str:
    """Render articles as a numbered plain-text list for the prompt."""
    lines: list[str] = []
    for i, article in enumerate(articles, start=1):
        lines.append(f"{i}. [{article.source}] {article.title}")
        lines.append(f"   URL: {article.url}")
        if article.content:
            # Trim long content to avoid exceeding context limits
            snippet = article.content[:1000].replace("\n", " ")
            lines.append(f"   Content: {snippet}")
        lines.append("")
    return "\n".join(lines)


def _extract_json_array(text: str) -> str:
    """
    Extract the first JSON array from a string that may contain markdown fences.

    Tries in order:
    1. Content inside a ```json ... ``` fence.
    2. Content inside a ``` ... ``` fence.
    3. The substring from the first ``[`` to the last ``]``.

    Raises:
        ValueError: If no JSON array boundary is found.
    """
    # Try fenced code block first
    fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    # Fall back to raw bracket extraction
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    raise ValueError(f"No JSON array found in Bedrock response: {text!r}")
