# tech-news-agent

> An AI agent that automatically discovers technology news, summarises it with **Amazon Bedrock**, and publishes content to **configurable output platforms** (blog, LinkedIn, Instagram, YouTube) — powered by **AWS AgentCore**.

---

## Overview

`tech-news-agent` is a fully serverless, event-driven AI agent built on AWS.  
It demonstrates production patterns for building and deploying intelligent agents using the AWS AgentCore framework.

**Workflow:**

1. **Amazon EventBridge** triggers the agent on a schedule.
2. **AWS AgentCore** starts the AI reasoning loop.
3. The agent fetches technology news from trusted sources.
4. Duplicate or low-quality articles are filtered via **Amazon DynamoDB**.
5. **Amazon Bedrock** summarises the selected articles into a `ContentPackage`.
6. **Amazon Bedrock** composes platform-specific posts for each enabled publisher.
7. Content is delivered to all configured output platforms in parallel.
8. Processed article URLs are recorded in DynamoDB to prevent duplicates.

**Output platforms are fully configurable** — enable any combination via the `ENABLED_PUBLISHERS` environment variable.

---

## Technology stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.13 |
| Agent framework | AWS AgentCore |
| LLM | Amazon Bedrock (Claude) |
| Infrastructure as Code | AWS CDK (Python) |
| Scheduling | Amazon EventBridge |
| State store | Amazon DynamoDB |
| Secrets | AWS SSM Parameter Store |
| Observability | Amazon CloudWatch |
| AWS SDK | boto3 |
| Testing | pytest, moto |
| Linting | Ruff |
| Formatting | Black |
| CI/CD | GitHub Actions |

---

## Project structure

```
tech-news-agent/
├── agent/                      # Agent source code
│   ├── main.py                 # AgentCore handler entry point
│   ├── config.py               # Centralised configuration
│   ├── publishers/             # One module per output platform
│   │   ├── base.py             # BasePublisher + ContentPackage + PublishResult
│   │   ├── blog.py             # Blog / Markdown file publisher (default)
│   │   ├── linkedin.py         # LinkedIn Share API publisher
│   │   ├── instagram.py        # Meta Graph API publisher
│   │   └── youtube.py          # YouTube Data API v3 publisher
│   ├── models/                 # Shared data models
│   ├── prompts/
│   │   ├── system.md           # System-level Bedrock prompt
│   │   ├── summarize.md        # Article summarisation prompt
│   │   └── platforms/          # Platform-specific post generation prompts
│   │       ├── blog.md
│   │       ├── linkedin.md
│   │       ├── instagram.md
│   │       └── youtube.md
│   ├── tools/                  # AgentCore tool implementations
│   └── workflows/              # Pipeline orchestration
├── infrastructure/             # AWS CDK Infrastructure as Code
│   ├── app.py                  # CDK application entry point
│   ├── stacks/                 # CDK stack definitions
│   └── lib/                    # Reusable CDK L3 constructs
├── tests/                      # pytest test suite
│   └── publishers/             # Publisher unit tests (one file per platform)
├── docs/                       # Project documentation
├── scripts/                    # Helper scripts
├── .github/
│   ├── copilot-instructions.md # GitHub Copilot repo-wide instructions
│   ├── instructions/           # Copilot per-directory instructions
│   └── workflows/              # GitHub Actions CI/CD
├── pyproject.toml              # Python project metadata, Ruff, Black, pytest config
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
└── cdk.json                    # CDK application configuration
```

---

## Getting started

```bash
# 1. Clone the repository
git clone https://github.com/<your-org>/tech-news-agent.git
cd tech-news-agent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Run tests
pytest

# 5. Lint and format
ruff check .
black .
```

## Configuring publishers

Set the `ENABLED_PUBLISHERS` environment variable to control where content is published.
Use a comma-separated list of platform keys:

| Key | Publisher | Credentials required |
|-----|-----------|----------------------|
| `blog` | `BlogPublisher` | None — writes Markdown to `BLOG_OUTPUT_PATH` |
| `linkedin` | `LinkedInPublisher` | `/tech-news-agent/linkedin` in SSM Parameter Store |
| `instagram` | `InstagramPublisher` | `/tech-news-agent/instagram` in SSM Parameter Store |
| `youtube` | `YouTubePublisher` | `/tech-news-agent/youtube` in SSM Parameter Store |

```bash
# Default — safe for all environments, no credentials needed
ENABLED_PUBLISHERS=blog

# Multiple platforms
ENABLED_PUBLISHERS=blog,linkedin,instagram

# All platforms
ENABLED_PUBLISHERS=blog,linkedin,instagram,youtube
```

See [agent/publishers/README.md](agent/publishers/README.md) for the publisher architecture and [docs/development.md](docs/development.md) for full setup instructions.

---

## Security

- **No secrets are stored in this repository.**  
- All credentials are managed via **AWS SSM Parameter Store** (SecureString).
- AWS access in CI/CD uses **GitHub OIDC + IAM role assumption** — no static credentials.
- IAM roles follow the **principle of least privilege**.

---

## Roadmap

See [docs/roadmap.md](docs/roadmap.md) for the full roadmap.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture and component diagram |
| [docs/deployment.md](docs/deployment.md) | How to deploy to AWS |
| [docs/development.md](docs/development.md) | Local development setup and conventions |
| [docs/roadmap.md](docs/roadmap.md) | Planned features and milestones |

---

## License

TODO: Add licence file.
