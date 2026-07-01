---
applyTo: "tests/**"
---

# Test Writing Instructions

When writing tests for tech-news-agent:

## File placement

| What you're testing | Test file location |
|---------------------|--------------------|
| A publisher | `tests/publishers/test_<platform>.py` |
| A tool | `tests/tools/test_<tool_name>.py` |
| A workflow | `tests/workflows/test_<workflow_name>.py` |
| Config / models | `tests/test_<module>.py` |

## Publisher test template

```python
"""tests/publishers/test_<platform>.py"""

import pytest
from agent.publishers.<platform> import <Platform>Publisher
from agent.publishers.base import ContentPackage, ArticleSummary


@pytest.fixture
def package() -> ContentPackage:
    return ContentPackage(
        topic="Test Topic",
        digest="Test digest.",
        articles=[ArticleSummary(title="Art", url="https://example.com", summary="s", relevance_score=4)],
        keywords=["python", "aws"],
        raw_post="Test post body.",
    )


class Test<Platform>PublisherFormatContent:
    def test_returns_non_empty_string(self, package):
        p = <Platform>Publisher()
        result = p.format_content(package)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_does_not_exceed_char_limit(self, package):
        p = <Platform>Publisher()
        result = p.format_content(package)
        assert len(result) <= <PLATFORM_CHAR_LIMIT>


class Test<Platform>PublisherPublish:
    def test_publish_raises_not_implemented(self, package):
        p = <Platform>Publisher()
        with pytest.raises(NotImplementedError):
            p.publish("content")
```

## AWS mocking rules

- Use `moto` for all boto3 / AWS service calls.
- Always inject the boto3 client via the constructor:

```python
@moto.mock_secretsmanager
def test_something():
    client = boto3.client("secretsmanager", region_name="us-east-1")
    client.create_secret(Name="tech-news-agent/linkedin", SecretString='{"access_token": "x"}')
    publisher = LinkedInPublisher(secrets_client=client)
    ...
```

## General rules

- `assert` statements only — no `print()`.
- Test `format_content()` and `publish()` in separate test classes.
- Use `pytest.raises` for expected exceptions.
- Never use real credentials — use moto or fixture data.
- Test class names: `Test<Class><Method>` (e.g. `TestBlogPublisherFormatContent`).
