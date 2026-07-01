# tech-news-agent — GitHub Copilot Instructions

This file gives GitHub Copilot context about the project so suggestions
are accurate and consistent with the codebase conventions.

## Project purpose

`tech-news-agent` is a **production-quality, serverless AI agent** built on
**AWS AgentCore** and **Amazon Bedrock**.  It discovers technology news,
summarises it, and publishes formatted content to one or more configurable
output platforms (blog, LinkedIn, Instagram, YouTube).

## Technology stack

- **Language:** Python 3.13 — use modern syntax (`match`, `|` unions, `list[str]`, `dict[str, int]`, etc.)
- **Agent framework:** AWS AgentCore
- **LLM:** Amazon Bedrock (Claude via `boto3`)
- **Infrastructure:** AWS CDK v2 (Python)
- **Testing:** pytest + moto for AWS mocking
- **Linting:** Ruff · **Formatting:** Black (line length 100)

## Architecture overview

```
EventBridge → AgentCore → news_pipeline workflow
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               fetch news  deduplicate  summarise (Bedrock)
                                            │
                                     ContentPackage
                                            │
                              ┌─────────────┼──────────────┐
                              ▼             ▼              ▼
                         BlogPublisher  LinkedInPublisher  ...
```

## Directory structure

| Path | Purpose |
|------|---------|
| `agent/` | All agent source code |
| `agent/publishers/` | One module per output platform — each subclasses `BasePublisher` |
| `agent/prompts/platforms/` | Bedrock prompt templates, one per platform |
| `agent/tools/` | AgentCore tool definitions |
| `agent/workflows/` | Pipeline orchestration |
| `agent/models/` | Shared data models |
| `infrastructure/` | AWS CDK stacks and constructs |
| `tests/` | pytest test suite |

## Coding conventions

### General
- All functions and methods must have complete type annotations.
- Use `from __future__ import annotations` at the top of every module.
- Use `logging.getLogger(__name__)` — never `print()`.
- Prefer `dataclass` for simple data holders; use Pydantic when validation is needed.
- Keep functions short (≤ 30 lines). Extract helpers when needed.

### Imports
- Absolute imports only (e.g. `from agent.publishers.base import BasePublisher`).
- Group: stdlib → third-party → local (`agent.*`).
- Ruff enforces import order automatically.

### Error handling
- Never swallow exceptions silently.
- Raise descriptive exceptions with context.
- Use structured logging (`logger.exception(...)`) for unexpected errors.

### Secrets
- **Never** hard-code credentials, tokens, or keys — not even placeholder strings.
- Use `AgentConfig.*_SECRET_NAME` constants to look up secrets at runtime from AWS Secrets Manager.
- Use environment variables only for non-sensitive configuration.

### AWS
- Always inject boto3 clients via constructor parameters so tests can mock them.
- Use `us-east-1` as the default region (overridden by `AWS_REGION` env var).
- Tag all CDK resources with `Project=tech-news-agent` and `Environment=<env>`.

## Publisher pattern

Every publisher follows this contract:

```python
class MyPlatformPublisher(BasePublisher):
    platform_name = "myplatform"

    def format_content(self, package: ContentPackage) -> str:
        # Transform ContentPackage into platform text
        ...

    def publish(self, content: str) -> PublishResult:
        # Deliver content to the platform API
        # Fetch credentials from Secrets Manager here
        ...
```

Register in `agent/publishers/__init__.py` → `PUBLISHER_REGISTRY`.

## Testing conventions

- Every publisher module must have a corresponding test file in `tests/publishers/`.
- Mock all AWS calls with `moto`.
- Inject boto3 clients via constructor so tests don't need `moto` for non-AWS publishers.
- Test `format_content()` and `publish()` independently.
- Use `pytest.raises(NotImplementedError)` for unimplemented stubs.

## What NOT to do

- Do not hard-code credentials or API keys — not even fake ones.
- Do not add business logic to `infrastructure/` — CDK only.
- Do not bypass Ruff or Black with `# noqa` without a comment explaining why.
- Do not add `print()` statements to production code.
- Do not commit `cdk.out/`, `.env`, or `*.pem` files.
