# Development Guide

Everything you need to develop, test, and extend the tech-news-agent locally.

---

## Table of contents

1. [Local setup](#1-local-setup)
2. [Running tests](#2-running-tests)
3. [Linting and formatting](#3-linting-and-formatting)
4. [Project conventions](#4-project-conventions)
5. [Adding a new publisher](#5-adding-a-new-publisher)
6. [Running the agent locally](#6-running-the-agent-locally)
7. [Working with secrets locally](#7-working-with-secrets-locally)
8. [Branch and PR strategy](#8-branch-and-pr-strategy)

---

## 1. Local setup

```bash
# Clone
git clone https://github.com/<your-org>/tech-news-agent.git
cd tech-news-agent

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate     # macOS / Linux
.venv\Scripts\activate        # Windows PowerShell

# Install all development dependencies
pip install -r requirements-dev.txt

# Verify the install
pytest --version
ruff --version
black --version
```

---

## 2. Running tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=agent --cov-report=term-missing

# Run a specific file
pytest tests/publishers/test_blog.py -v

# Run a specific test class or function
pytest tests/publishers/test_blog.py::TestBlogPublisherPublish -v
pytest tests/publishers/test_blog.py::TestBlogPublisherPublish::test_publish_creates_file -v

# Run tests matching a keyword
pytest -k "blog" -v
```

### Test structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_agent.py            # Handler entry point tests
├── test_config.py           # AgentConfig tests
└── publishers/              # One file per publisher platform
    ├── test_registry.py     # Publisher registry / factory tests
    ├── test_blog.py         # BlogPublisher (fully functional)
    ├── test_linkedin.py     # LinkedInPublisher — format, credentials, publish, dry-run
    ├── test_instagram.py    # InstagramPublisher
    └── test_youtube.py      # YouTubePublisher
```

---

## 3. Linting and formatting

The project uses **Ruff** (linting + import sorting) and **Black** (formatting).
Configuration lives in `pyproject.toml`.

```bash
# Check for lint errors
ruff check .

# Auto-fix fixable issues
ruff check . --fix

# Check formatting (no changes made)
black --check .

# Apply formatting
black .

# Run both in one go (lint then format)
ruff check . --fix ; black .
```

Run these before every commit.  The CI pipeline enforces them on pull requests.

---

## 4. Project conventions

### Module structure

Every Python module must have:
- A module-level docstring with description and TODO section.
- `from __future__ import annotations` as the first import.
- `logger = logging.getLogger(__name__)` — never `print()`.
- Full type annotations on all function signatures.

### Imports

```python
from __future__ import annotations

# stdlib
import logging
import os
from dataclasses import dataclass

# third-party
import boto3

# local (absolute only — no relative imports)
from agent.config import AgentConfig
from agent.publishers.base import BasePublisher, ContentPackage
```

### Secrets rule

Never hard-code credential values.  Always:
1. Define a parameter path constant in `AgentConfig` (e.g. `LINKEDIN_PARAM_PATH`).
2. Fetch the value at runtime with `boto3` SSM Parameter Store.
3. Inject the `ssm_client` via constructor so tests can mock it.

```python
# Correct
def _get_credentials(self, ssm_client) -> dict:
    import json
    response = ssm_client.get_parameter(Name=AgentConfig.LINKEDIN_PARAM_PATH, WithDecryption=True)
    return json.loads(response["Parameter"]["Value"])

# WRONG — never do this
access_token = "AQICAHh..."  # ← hard-coded secret
```

### AWS clients

Always inject boto3 clients via constructor so tests can pass a moto mock:

```python
class MyTool:
    def __init__(self, dynamodb_client=None):
        self._db = dynamodb_client or boto3.client("dynamodb", region_name=AgentConfig.aws_region)
```

---

## 5. Adding a new publisher

Follow the checklist in [`.github/instructions/publishers.instructions.md`](../.github/instructions/publishers.instructions.md).

Quick summary:

1. **Create the module** — `agent/publishers/<platform>.py`
   - Subclass `BasePublisher`.
   - Set `platform_name = "<platform>"`.
   - Implement `format_content(package) → str`.
   - Implement `publish(content) → PublishResult` (fetch credentials from SSM Parameter Store).

2. **Add the prompt** — `agent/prompts/platforms/<platform>.md`
   - Document the Bedrock prompt template for this platform.
   - Include format rules, length limits, and output instructions.

3. **Register it** — `agent/publishers/__init__.py`
   ```python
   from agent.publishers.<platform> import <Platform>Publisher
   PUBLISHER_REGISTRY["<platform>"] = <Platform>Publisher
   ```

4. **Add the parameter path** — `agent/config.py`
   ```python
   <PLATFORM>_PARAM_PATH: str = "/tech-news-agent/<platform>"
   ```

5. **Write tests** — `tests/publishers/test_<platform>.py`
   - Test `format_content()` independently.
   - Test `publish()` raises `NotImplementedError` (until implemented).
   - Use `moto` to mock SSM Parameter Store when credentials are fetched.

6. **Update `agent/publishers/README.md`** — add a row to the platform table.

7. **Create the AWS parameter** — see [Credentials setup](deployment.md#3-configure-credentials-in-aws-ssm-parameter-store).

8. **Enable it** — set `ENABLED_PUBLISHERS=...,<platform>` in your environment.

---

## 6. Running the agent locally

Use `scripts/run_local.py` to run the full pipeline end-to-end against real AWS services.

### Setup

```bash
# Copy the example env file and edit it (AWS_REGION is the only required change)
cp .env.example .env.local
```

Edit `.env.local` — at minimum set `AWS_REGION`. If you use a non-default AWS profile, also set `AWS_PROFILE`.

### Run

```bash
# Safe first run — generates and tracks the post in DynamoDB, does NOT post to LinkedIn
python scripts/run_local.py --dry-run

# If the pipeline exits early ("No new articles"), bypass deduplication
python scripts/run_local.py --dry-run --force-new

# Use OpenAI instead of Bedrock
LLM_PROVIDER=openai python scripts/run_local.py --dry-run --force-new

# When ready to actually post to LinkedIn:
# 1. Set ENABLE_POSTING=true in .env.local
# 2. Remove --dry-run
python scripts/run_local.py --force-new
```

The script prints a config summary on startup and the pipeline result on exit.  
All logs are printed to the console at INFO level.

### What happens locally vs in Lambda

| Concern | Local | Lambda |
|---------|-------|--------|
| AWS credentials | `~/.aws/credentials` (boto3 credential chain) | IAM execution role |
| SSM secrets | Fetched from real Parameter Store | Fetched from real Parameter Store |
| DynamoDB | Real tables in your account | Real tables in your account |
| Logging | Console (stdout) | CloudWatch Logs |

---

## 7. Working with secrets locally

During local development you do not need real credentials to run tests —
`moto` mocks all AWS calls.

If you want to test against real AWS services locally:

```bash
# Set your AWS profile
export AWS_PROFILE=my-dev-profile
export AWS_REGION=us-east-1

# Optionally point at a specific SSM endpoint (e.g. LocalStack)
export AWS_ENDPOINT_URL=http://localhost:4566
```

### Using LocalStack for offline development

[LocalStack](https://localstack.cloud/) emulates AWS services locally:

```bash
# Install LocalStack
pip install localstack

# Start LocalStack
localstack start

# Create parameters in LocalStack
aws --endpoint-url=http://localhost:4566 ssm put-parameter \
    --name "/tech-news-agent/linkedin" \
    --type SecureString \
    --value '{"access_token": "local-fake-token", "author_urn": "urn:li:person:test"}'
```

---

## 8. Branch and PR strategy

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code — protected, requires PR |
| `develop` | Integration branch |
| `feature/<name>` | New features |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation-only changes |

### Before opening a PR

```bash
# All tests must pass
pytest

# No lint errors
ruff check .

# Code is formatted
black --check .
```

The CI workflow (`.github/workflows/ci.yml`) enforces these on every PR
targeting `main` or `develop`.
