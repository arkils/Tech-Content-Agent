# tests

This directory contains the test suite for tech-news-agent, using [pytest](https://pytest.org/).

## Structure

```
tests/
├── conftest.py         # Shared fixtures
├── test_agent.py       # Tests for the agent entry point
├── test_config.py      # Tests for AgentConfig
└── README.md           # This file
```

## Running tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=agent --cov-report=term-missing

# Run a single file
pytest tests/test_config.py -v
```

## TODO

- Add `unit/` subdirectory with tests for each tool.
- Add `integration/` subdirectory for end-to-end tests against real AWS services.
- Achieve ≥ 80 % code coverage before first production deployment.
