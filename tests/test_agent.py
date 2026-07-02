"""
tests/test_agent.py
===================
Unit tests for agent/main.py (entry point / handler).
"""

from unittest.mock import MagicMock, patch

import pytest

from agent.main import handler


class TestHandler:
    """Tests for the AgentCore handler entry point."""

    def _make_pipeline_result(self, skipped: bool = False) -> MagicMock:
        result = MagicMock()
        result.skipped = skipped
        result.skip_reason = "No new articles" if skipped else ""
        result.articles_fetched = 5
        result.articles_new = 0 if skipped else 3
        result.summaries_produced = 0 if skipped else 3
        result.publish_results = []
        return result

    def test_handler_returns_dict(self) -> None:
        with patch("agent.main.boto3"), patch(
            "agent.main.NewsPipeline"
        ) as mock_pipeline_cls:
            mock_pipeline_cls.return_value.run.return_value = self._make_pipeline_result()
            response = handler(event={}, context=object())
        assert isinstance(response, dict)

    def test_handler_response_has_status(self) -> None:
        with patch("agent.main.boto3"), patch(
            "agent.main.NewsPipeline"
        ) as mock_pipeline_cls:
            mock_pipeline_cls.return_value.run.return_value = self._make_pipeline_result()
            response = handler(event={}, context=object())
        assert "status" in response

    def test_handler_status_ok_when_not_skipped(self) -> None:
        with patch("agent.main.boto3"), patch(
            "agent.main.NewsPipeline"
        ) as mock_pipeline_cls:
            mock_pipeline_cls.return_value.run.return_value = self._make_pipeline_result(skipped=False)
            response = handler(event={}, context=object())
        assert response["status"] == "ok"

    def test_handler_status_skipped_when_pipeline_skips(self) -> None:
        with patch("agent.main.boto3"), patch(
            "agent.main.NewsPipeline"
        ) as mock_pipeline_cls:
            mock_pipeline_cls.return_value.run.return_value = self._make_pipeline_result(skipped=True)
            response = handler(event={}, context=object())
        assert response["status"] == "skipped"

    def test_handler_response_contains_pipeline_stats(self) -> None:
        with patch("agent.main.boto3"), patch(
            "agent.main.NewsPipeline"
        ) as mock_pipeline_cls:
            mock_pipeline_cls.return_value.run.return_value = self._make_pipeline_result()
            response = handler(event={}, context=object())
        assert "articles_fetched" in response
        assert "articles_new" in response
        assert "summaries_produced" in response

