# Development Q&A

## Q: How do I set up the project locally?

```bash
# Clone
git clone https://github.com/<your-org>/tech-news-agent.git
cd tech-news-agent

# Virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows PowerShell

# Install all dev dependencies
pip install -r requirements-dev.txt

# Verify
pytest --version
ruff --version
black --version
```

---

## Q: How do I run the tests?

```bash
# All tests
pytest

# With coverage
pytest --cov=agent --cov-report=term-missing

# Publisher tests only
pytest tests/publishers/ -v

# A specific test file
pytest tests/publishers/test_blog.py -v

# A specific test class
pytest tests/publishers/test_blog.py::TestBlogPublisherPublish -v

# A specific test function
pytest tests/publishers/test_blog.py::TestBlogPublisherPublish::test_publish_creates_file -v

# By keyword
pytest -k "blog" -v
```

Current test count: **39 tests, all passing**.

---

## Q: Where are the tests?

```
tests/
├── conftest.py              # Shared fixtures (sample_article)
├── test_agent.py            # handler() entry point tests
├── test_config.py           # AgentConfig tests
└── publishers/
    ├── __init__.py
    ├── test_registry.py     # PUBLISHER_REGISTRY + get_active_publishers()
    ├── test_blog.py         # Full BlogPublisher tests
    ├── test_linkedin.py     # LinkedInPublisher format + NotImplementedError
    ├── test_instagram.py    # InstagramPublisher format + NotImplementedError
    └── test_youtube.py      # YouTubePublisher format + NotImplementedError
```

---

## Q: How do I lint and format the code?

The project uses **Ruff** (lint + import sort) and **Black** (format). Both are configured in `pyproject.toml`.

```bash
# Lint check (no changes)
ruff check .

# Auto-fix fixable issues
ruff check . --fix

# Format check (no changes)
black --check .

# Apply formatting
black .

# Combined: fix then format
ruff check . --fix ; black .
```

Run these before every commit. CI enforces both on PRs.

---

## Q: How do I write a test for a publisher?

Follow `.github/instructions/tests.instructions.md` for the full template.

Minimum tests for a publisher:

```python
# tests/publishers/test_<platform>.py
import pytest
from agent.publishers.<platform> import <Platform>Publisher
from agent.publishers.base import ContentPackage, ArticleSummary

@pytest.fixture
def package() -> ContentPackage:
    return ContentPackage(
        topic="Test", digest="Digest.", articles=[
            ArticleSummary(title="A", url="https://x.com", summary="S", relevance_score=4)
        ], keywords=["python"], raw_post="Post body."
    )

class Test<Platform>PublisherFormatContent:
    def test_returns_non_empty_string(self, package):
        result = <Platform>Publisher().format_content(package)
        assert isinstance(result, str) and len(result) > 0

class Test<Platform>PublisherPublish:
    def test_publish_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            <Platform>Publisher().publish("content")
```

---

## Q: How do I mock AWS services in tests?

Use `moto`. Inject the boto3 client via constructor:

```python
import boto3
import moto
import pytest

@pytest.fixture
def secrets_client():
    with moto.mock_aws():
        client = boto3.client("secretsmanager", region_name="us-east-1")
        client.create_secret(
            Name="tech-news-agent/linkedin",
            SecretString='{"access_token": "fake-token", "author_urn": "urn:li:person:123"}'
        )
        yield client

def test_publish_uses_credentials(secrets_client):
    publisher = LinkedInPublisher(secrets_client=secrets_client)
    # ... test publish() once implemented
```

---

## Q: How do I run the agent locally without deploying?

The full agent requires the pipeline to be implemented. For now, exercise `BlogPublisher` directly:

```python
from agent.publishers.blog import BlogPublisher
from agent.publishers.base import ContentPackage, ArticleSummary

package = ContentPackage(
    topic="Local Test Run",
    digest="Testing locally.",
    articles=[ArticleSummary(title="Art", url="https://x.com", summary="s", relevance_score=4, source="X")],
    keywords=["python", "aws"],
    raw_post="This is a local test post.",
)

result = BlogPublisher(output_dir="output/test").run(package)
print(result)
# PublishResult(platform='blog', success=True, url='output/test/2026-07-01-abc12345.md', ...)
```

---

## Q: How do I use LocalStack for offline AWS development?

[LocalStack](https://localstack.cloud/) emulates AWS services locally — no real AWS account needed.

```bash
# Install
pip install localstack

# Start
localstack start

# Create a secret in LocalStack
aws --endpoint-url=http://localhost:4566 secretsmanager create-secret \
    --name "tech-news-agent/linkedin" \
    --secret-string '{"access_token": "local-token", "author_urn": "urn:li:person:test"}'

# Point your code at LocalStack
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_REGION=us-east-1
```

---

## Q: What are the coding conventions?

| Convention | Rule |
|------------|------|
| `from __future__ import annotations` | Top of every module |
| Logging | `logger = logging.getLogger(__name__)` — never `print()` |
| Imports | Absolute only: `from agent.publishers.base import ...` |
| Type annotations | All function signatures must be fully annotated |
| Secrets | Never hard-code values — use `AgentConfig.*_SECRET_NAME` |
| boto3 clients | Inject via constructor for testability |
| Function length | ≤ 30 lines — extract helpers if longer |
| AWS region | Default `us-east-1`, overridden by `AWS_REGION` env var |

---

## Q: What is the branch strategy?

| Branch | Purpose | Rules |
|--------|---------|-------|
| `main` | Production-ready | Protected — PR + CI required |
| `develop` | Integration | Merge feature branches here first |
| `feature/<name>` | New features | Branch from `develop` |
| `fix/<name>` | Bug fixes | Branch from `main` or `develop` |
| `docs/<name>` | Docs only | Branch from `develop` |

**PR checklist before merging:**
```bash
pytest                 # all tests pass
ruff check .           # no lint errors
black --check .        # code is formatted
```

---

## Q: What does the pyproject.toml configure?

`pyproject.toml` at the repo root configures:

- **`[tool.ruff]`** — target Python 3.13, line length 100, enabled rule sets (pyflakes, isort, bugbear, bandit security checks, pep8-naming, etc.)
- **`[tool.black]`** — line length 100, target Python 3.13
- **`[tool.pytest.ini_options]`** — test paths, `--strict-markers`, `-v`
- **`[tool.coverage.run]`** — coverage source is `agent/`, omitting tests and infrastructure

---

## Q: What is in requirements-dev.txt vs requirements.txt?

- **`requirements.txt`** — runtime dependencies only: `boto3`, `aws-cdk-lib`, `constructs`
- **`requirements-dev.txt`** — includes `-r requirements.txt` plus: `pytest`, `pytest-cov`, `ruff`, `black`, `moto[all]`

Always use `requirements-dev.txt` for local development.
