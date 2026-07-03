"""
tests/test_post_generator.py
=============================
Unit tests for agent/tools/post_generator.py.

Bedrock is mocked via unittest.mock.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import io
import json

import pytest

from agent.models import ArticleSummary, ContentPackage
from agent.tools.post_generator import (
    PostGenerator,
    _derive_digest,
    _derive_keywords,
    _derive_topic,
    _extract_prompt_block,
    _serialise_summaries,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(n: int, score: int = 3) -> ArticleSummary:
    return ArticleSummary(
        title=f"AI Model Release {n}",
        url=f"https://example.com/article-{n}",
        summary=f"Summary of article {n}. It covers recent AI developments.",
        relevance_score=score,
        source="Tech News",
    )


def _make_bedrock_response(text: str) -> dict:
    return {
        "output": {
            "message": {
                "content": [{"text": text}]
            }
        }
    }


def _make_generator(post_text: str = "Generated LinkedIn post text.") -> PostGenerator:
    client = MagicMock()
    client.converse.return_value = _make_bedrock_response(post_text)
    return PostGenerator(bedrock_client=client)


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestPostGeneratorRun:
    def test_returns_content_package(self) -> None:
        generator = _make_generator()
        result = generator.run([_make_summary(1)], platform="linkedin")
        assert isinstance(result, ContentPackage)

    def test_content_package_has_raw_post(self) -> None:
        generator = _make_generator("My LinkedIn post.")
        result = generator.run([_make_summary(1)], platform="linkedin")
        assert result.raw_post == "My LinkedIn post."

    def test_content_package_has_topic(self) -> None:
        generator = _make_generator()
        result = generator.run([_make_summary(1)], platform="linkedin")
        assert result.topic != ""

    def test_content_package_has_articles(self) -> None:
        summaries = [_make_summary(1), _make_summary(2)]
        generator = _make_generator()
        result = generator.run(summaries, platform="linkedin")
        assert result.articles == summaries

    def test_content_package_has_keywords(self) -> None:
        generator = _make_generator()
        result = generator.run([_make_summary(1)], platform="linkedin")
        assert isinstance(result.keywords, list)

    def test_content_package_has_digest(self) -> None:
        generator = _make_generator()
        result = generator.run([_make_summary(1)], platform="linkedin")
        assert result.digest != ""

    def test_raises_for_unsupported_platform(self) -> None:
        generator = _make_generator()
        with pytest.raises(ValueError, match="not supported"):
            generator.run([_make_summary(1)], platform="instagram")

    def test_raises_for_empty_summaries(self) -> None:
        generator = _make_generator()
        with pytest.raises(ValueError, match="empty"):
            generator.run([], platform="linkedin")

    def test_bedrock_called_with_correct_model(self) -> None:
        from agent.config import AgentConfig
        client = MagicMock()
        client.converse.return_value = _make_bedrock_response("Post text.")
        generator = PostGenerator(bedrock_client=client)
        generator.run([_make_summary(1)], platform="linkedin")
        call_kwargs = client.converse.call_args[1]
        assert call_kwargs["modelId"] == AgentConfig.bedrock_model_id

    def test_prompt_sent_to_bedrock_contains_topic(self) -> None:
        client = MagicMock()
        client.converse.return_value = _make_bedrock_response("Post.")
        generator = PostGenerator(bedrock_client=client)
        summary = ArticleSummary(
            title="Quantum Computing Milestone",
            url="https://x.com",
            summary="Big news in quantum.",
            relevance_score=5,
        )
        generator.run([summary], platform="linkedin")
        call_kwargs = client.converse.call_args[1]
        prompt = call_kwargs["messages"][0]["content"][0]["text"]
        assert "Quantum Computing Milestone" in prompt

    def test_uses_configured_model_id(self) -> None:
        client = MagicMock()
        client.invoke_model.return_value = {
            "body": io.BytesIO(
                json.dumps(
                    {"output": {"message": {"content": [{"text": "Post text."}]}}}
                ).encode("utf-8")
            )
        }
        generator = PostGenerator(bedrock_client=client)
        generator._config = type("Config", (), {"bedrock_model_id": "amazon.nova-lite-v1:0"})()

        result = generator.run([_make_summary(1)], platform="linkedin")

        assert result.raw_post == "Post text."
        client.invoke_model.assert_called_once()
        assert client.invoke_model.call_args.kwargs["modelId"] == "amazon.nova-lite-v1:0"

    def test_raises_on_no_text_in_bedrock_response(self) -> None:
        client = MagicMock()
        client.converse.return_value = {"output": {"message": {"content": []}}}
        generator = PostGenerator(bedrock_client=client)
        with pytest.raises(RuntimeError, match="no text content"):
            generator.run([_make_summary(1)], platform="linkedin")

    def test_raises_when_prompt_template_missing(self, tmp_path: Path) -> None:
        client = MagicMock()
        generator = PostGenerator(bedrock_client=client, prompts_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            generator.run([_make_summary(1)], platform="linkedin")


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


class TestDeriveTopic:
    def test_returns_title_of_highest_score(self) -> None:
        summaries = [_make_summary(1, score=2), _make_summary(2, score=5)]
        assert _derive_topic(summaries) == "AI Model Release 2"

    def test_single_summary(self) -> None:
        assert _derive_topic([_make_summary(1, score=3)]) == "AI Model Release 1"


class TestDeriveKeywords:
    def test_returns_list(self) -> None:
        result = _derive_keywords([_make_summary(1)])
        assert isinstance(result, list)

    def test_excludes_stop_words(self) -> None:
        summary = ArticleSummary(
            title="The New AI Model", url="https://x.com", summary="S.", relevance_score=3
        )
        keywords = _derive_keywords([summary])
        lower = [k.lower() for k in keywords]
        assert "the" not in lower
        assert "new" not in lower

    def test_caps_at_ten(self) -> None:
        summaries = [
            ArticleSummary(
                title=f"Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda{i}",
                url=f"https://x.com/{i}",
                summary="S.",
                relevance_score=3,
            )
            for i in range(5)
        ]
        assert len(_derive_keywords(summaries)) <= 10

    def test_deduplicates_words(self) -> None:
        summaries = [_make_summary(1), _make_summary(2)]
        keywords = _derive_keywords(summaries)
        lower = [k.lower() for k in keywords]
        assert len(lower) == len(set(lower))


class TestDeriveDigest:
    def test_returns_string(self) -> None:
        assert isinstance(_derive_digest([_make_summary(1)]), str)

    def test_ends_with_period(self) -> None:
        result = _derive_digest([_make_summary(1)])
        assert result.endswith(".")

    def test_uses_top_scoring_article(self) -> None:
        low = ArticleSummary(
            title="Low", url="https://x.com/low", summary="Low relevance summary.", relevance_score=1
        )
        high = ArticleSummary(
            title="High", url="https://x.com/high", summary="High relevance summary.", relevance_score=5
        )
        result = _derive_digest([low, high])
        assert "High relevance" in result


class TestExtractPromptBlock:
    def test_extracts_fenced_block(self) -> None:
        template = "# Title\n\nSome docs.\n\n```\nActual prompt text.\n```\n\nMore docs."
        assert _extract_prompt_block(template) == "Actual prompt text."

    def test_returns_full_text_when_no_fence(self) -> None:
        template = "Just a plain prompt with no fences."
        assert _extract_prompt_block(template) == "Just a plain prompt with no fences."


class TestSerialiseSummaries:
    def test_includes_title_and_url(self) -> None:
        result = _serialise_summaries([_make_summary(1)])
        assert "AI Model Release 1" in result
        assert "https://example.com/article-1" in result

    def test_includes_relevance_score(self) -> None:
        result = _serialise_summaries([_make_summary(1, score=4)])
        assert "4/5" in result

    def test_numbers_summaries(self) -> None:
        result = _serialise_summaries([_make_summary(1), _make_summary(2)])
        assert "1." in result
        assert "2." in result

    def test_empty_returns_empty_string(self) -> None:
        assert _serialise_summaries([]) == ""
