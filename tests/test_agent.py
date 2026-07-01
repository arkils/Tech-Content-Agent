"""
tests/test_agent.py
===================
Unit tests for agent/main.py (entry point / handler).

TODO:
    - Test that handler raises NotImplementedError until implemented (placeholder).
    - Test that handler returns a valid AgentCore response shape once implemented.
    - Test that the handler logs the incoming event.
    - Mock all external AWS calls with moto.
"""

import pytest

from agent.main import handler


class TestHandler:
    """Tests for the AgentCore handler entry point."""

    def test_handler_raises_not_implemented(self) -> None:
        """
        Handler must raise NotImplementedError until the pipeline is wired up.
        Remove this test when the handler is implemented.
        """
        with pytest.raises(NotImplementedError):
            handler(event={}, context=object())

    # TODO: add tests for valid event processing once handler is implemented
    # TODO: add tests for error handling and structured error responses
