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

import json
import logging
import re
from pathlib import Path
from typing import Any

import boto3
import requests

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
        """Call Bedrock first and fall back to OpenAI if Bedrock fails."""
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
                return _extract_text(payload).strip()

            response = self._bedrock.converse(
                modelId=self._config.bedrock_model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
            )
            return _extract_text(response).strip()
        except Exception as exc:
            logger.warning("Bedrock request failed, falling back to OpenAI: %s", exc)
            return self._call_openai(prompt)

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
            "model": "gpt-4.1-mini",
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
