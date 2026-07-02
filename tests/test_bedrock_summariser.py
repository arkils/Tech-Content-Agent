"""
tests/test_bedrock_summariser.py
=================================
Unit tests for agent/tools/bedrock_summariser.py.

Bedrock is mocked via unittest.mock — no moto needed since bedrock-runtime
is not a stateful AWS service.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent.models import Article, ArticleSummary
from agent.tools.bedrock_summariser import (
    ArticleSummariser,
    _extract_json_array,
    _serialise_articles,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_article(n: int, content: str = "Body text.") -> Article:
    return Article(
        url=f"https://example.com/article-{n}",
        title=f"Article {n}",
        source="Ars Technica",
        published_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
        content=content,
    )


def _make_bedrock_response(items: list[dict]) -> dict:
    """Build a minimal Bedrock converse response dict."""
    return {
        "output": {
            "message": {
                "content": [{"text": json.dumps(items)}]
            }
        }
    }


def _make_summariser(bedrock_response: dict) -> ArticleSummariser:
    client = MagicMock()
    client.converse.return_value = bedrock_response
    return ArticleSummariser(bedrock_client=client)


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestArticleSummariserRun:
    def test_returns_article_summaries(self) -> None:
        response = _make_bedrock_response([
            {
                "title": "Article 1",
                "url": "https://example.com/article-1",
                "summary": "A great summary.",
                "relevance_score": 4,
                "duplicate_of": None,
            }
        ])
        summariser = _make_summariser(response)
        result = summariser.run([_make_article(1)])

        assert len(result) == 1
        assert isinstance(result[0], ArticleSummary)
        assert result[0].title == "Article 1"
        assert result[0].relevance_score == 4

    def test_returns_empty_list_for_empty_input(self) -> None:
        client = MagicMock()
        summariser = ArticleSummariser(bedrock_client=client)

        result = summariser.run([])

        assert result == []
        client.converse.assert_not_called()

    def test_drops_duplicate_flagged_articles(self) -> None:
        response = _make_bedrock_response([
            {
                "title": "Original",
                "url": "https://example.com/original",
                "summary": "Original story.",
                "relevance_score": 5,
                "duplicate_of": None,
            },
            {
                "title": "Duplicate",
                "url": "https://example.com/duplicate",
                "summary": "Same story.",
                "relevance_score": 3,
                "duplicate_of": "https://example.com/original",
            },
        ])
        summariser = _make_summariser(response)
        result = summariser.run([_make_article(1), _make_article(2)])

        assert len(result) == 1
        assert result[0].title == "Original"

    def test_multiple_articles_returned(self) -> None:
        items = [
            {
                "title": f"Article {i}",
                "url": f"https://example.com/article-{i}",
                "summary": f"Summary {i}.",
                "relevance_score": i % 5 + 1,
                "duplicate_of": None,
            }
            for i in range(5)
        ]
        response = _make_bedrock_response(items)
        summariser = _make_summariser(response)
        result = summariser.run([_make_article(i) for i in range(5)])

        assert len(result) == 5

    def test_bedrock_called_with_correct_model_id(self) -> None:
        from agent.config import AgentConfig

        client = MagicMock()
        client.converse.return_value = _make_bedrock_response([
            {
                "title": "T",
                "url": "https://x.com",
                "summary": "S.",
                "relevance_score": 3,
                "duplicate_of": None,
            }
        ])
        summariser = ArticleSummariser(bedrock_client=client)
        summariser.run([_make_article(1)])

        call_kwargs = client.converse.call_args[1]
        assert call_kwargs["modelId"] == AgentConfig.bedrock_model_id

    def test_raises_on_no_text_in_response(self) -> None:
        client = MagicMock()
        client.converse.return_value = {"output": {"message": {"content": []}}}
        summariser = ArticleSummariser(bedrock_client=client)

        with pytest.raises(RuntimeError, match="no text content"):
            summariser.run([_make_article(1)])

    def test_raises_on_invalid_json_response(self) -> None:
        client = MagicMock()
        client.converse.return_value = {
            "output": {"message": {"content": [{"text": "not valid json"}]}}
        }
        summariser = ArticleSummariser(bedrock_client=client)

        with pytest.raises(ValueError):
            summariser.run([_make_article(1)])

    def test_skips_incomplete_items(self) -> None:
        response = _make_bedrock_response([
            {"title": "", "url": "https://x.com", "summary": "", "duplicate_of": None},
            {
                "title": "Good",
                "url": "https://x.com/good",
                "summary": "Fine.",
                "relevance_score": 3,
                "duplicate_of": None,
            },
        ])
        summariser = _make_summariser(response)
        result = summariser.run([_make_article(1), _make_article(2)])

        assert len(result) == 1
        assert result[0].title == "Good"


# ---------------------------------------------------------------------------
# _parse_response — JSON extraction edge cases
# ---------------------------------------------------------------------------


class TestExtractJsonArray:
    def test_plain_json_array(self) -> None:
        text = '[{"a": 1}]'
        assert _extract_json_array(text) == '[{"a": 1}]'

    def test_json_fenced_code_block(self) -> None:
        text = '```json\n[{"a": 1}]\n```'
        result = _extract_json_array(text)
        assert json.loads(result) == [{"a": 1}]

    def test_plain_fenced_code_block(self) -> None:
        text = '```\n[{"a": 1}]\n```'
        result = _extract_json_array(text)
        assert json.loads(result) == [{"a": 1}]

    def test_array_embedded_in_prose(self) -> None:
        text = 'Here is the result:\n[{"x": 2}]\nEnd.'
        result = _extract_json_array(text)
        assert json.loads(result) == [{"x": 2}]

    def test_raises_when_no_array_found(self) -> None:
        with pytest.raises(ValueError, match="No JSON array"):
            _extract_json_array("No brackets here.")


# ---------------------------------------------------------------------------
# _serialise_articles
# ---------------------------------------------------------------------------


class TestSerialiseArticles:
    def test_includes_title_and_url(self) -> None:
        articles = [_make_article(1)]
        text = _serialise_articles(articles)
        assert "Article 1" in text
        assert "https://example.com/article-1" in text

    def test_includes_source(self) -> None:
        text = _serialise_articles([_make_article(1)])
        assert "Ars Technica" in text

    def test_includes_content_snippet(self) -> None:
        article = _make_article(1, content="Important tech news body.")
        text = _serialise_articles([article])
        assert "Important tech news body." in text

    def test_truncates_long_content(self) -> None:
        long_content = "x" * 2000
        article = _make_article(1, content=long_content)
        text = _serialise_articles([article])
        # Snippet is capped at 1000 chars
        assert "x" * 1001 not in text

    def test_numbers_articles(self) -> None:
        articles = [_make_article(i) for i in range(3)]
        text = _serialise_articles(articles)
        assert "1." in text
        assert "2." in text
        assert "3." in text

    def test_empty_list_returns_empty_string(self) -> None:
        assert _serialise_articles([]) == ""

    def test_prompt_template_placeholder_replaced(self) -> None:
        """The {{ARTICLES}} placeholder must be replaced in the built prompt."""
        client = MagicMock()
        client.converse.return_value = _make_bedrock_response([])
        summariser = ArticleSummariser(bedrock_client=client)
        summariser.run([_make_article(1)])

        call_kwargs = client.converse.call_args[1]
        prompt_text = call_kwargs["messages"][0]["content"][0]["text"]
        assert "{{ARTICLES}}" not in prompt_text
        assert "Article 1" in prompt_text
