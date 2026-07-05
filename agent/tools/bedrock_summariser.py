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
from typing import Any

import boto3
import requests

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
        """Route to the configured LLM provider.

        When ``LLM_PROVIDER=openai``, calls OpenAI directly without attempting Bedrock.
        When ``LLM_PROVIDER=bedrock`` (default), tries Bedrock first and falls back
        to OpenAI on any error.
        """
        if self._config.llm_provider == "openai":
            logger.info("LLM_PROVIDER=openai — routing directly to OpenAI")
            return self._call_openai(prompt)

        try:
            if self._config.bedrock_model_id.startswith("amazon.nova"):
                request_body = json.dumps(
                    {
                        "messages": [{"role": "user", "content": [{"text": prompt}]}],
                        "inferenceConfig": {"max_new_tokens": 2_000, "temperature": 0.2},
                    }
                )
                response = self._bedrock.invoke_model(
                    modelId=self._config.bedrock_model_id,
                    body=request_body,
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = response.get("body")
                if hasattr(response_body, "read"):
                    payload = json.loads(response_body.read().decode("utf-8"))
                else:
                    payload = json.loads(response_body.decode("utf-8"))
                return _extract_text(payload)

            response = self._bedrock.converse(
                modelId=self._config.bedrock_model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
            )
        except Exception as exc:
            logger.warning("Bedrock request failed, falling back to OpenAI: %s", exc)
            return self._call_openai(prompt)
        return _extract_text(response)

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI Chat Completions using an SSM-stored API key."""
        ssm_client = boto3.client("ssm", region_name=self._config.aws_region)
        response = ssm_client.get_parameter(
            Name=AgentConfig.OPENAI_API_PARAM_PATH, WithDecryption=True
        )
        creds = _parse_openai_credentials(response["Parameter"]["Value"])
        api_key = str(creds.get("api_key", "")).strip()
        if not api_key:
            raise RuntimeError("OpenAI API key is missing from SSM parameter store")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._config.openai_model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        http_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        http_response.raise_for_status()
        data = http_response.json()
        return data["choices"][0]["message"]["content"]

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


def _extract_text(payload: dict) -> str:
    """Extract assistant text from either Converse or InvokeModel responses."""
    output = payload.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])
    for block in content:
        if isinstance(block, dict) and block.get("text"):
            return block["text"]
    if isinstance(payload.get("outputText"), str):
        return payload["outputText"]
    raise RuntimeError(
        f"Bedrock returned no text content. Full response: {payload}"
    )


def _parse_openai_credentials(value: Any) -> dict[str, str]:
    """Parse OpenAI credentials from either JSON or a raw string value."""
    if isinstance(value, dict):
        return {key: str(val) for key, val in value.items() if isinstance(val, (str, int, float))}

    if not isinstance(value, str):
        return {}

    text = value.strip()
    if not text:
        return {}

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {key: str(val) for key, val in data.items() if isinstance(val, (str, int, float))}
    except json.JSONDecodeError:
        pass

    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\t\r\n")
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return {key: str(val) for key, val in data.items() if isinstance(val, (str, int, float))}
    except json.JSONDecodeError:
        pass

    match = re.search(r'"api_key"\s*:\s*"([^"]*)"', cleaned)
    if match:
        return {"api_key": match.group(1)}

    if text.startswith("sk"):
        return {"api_key": text}

    return {}


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
