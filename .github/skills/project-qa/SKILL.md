---
name: project-qa
description: "Answer questions about the tech-news-agent project. Use when: asked how something works, how to add a publisher, how to configure platforms, how to deploy, how secrets work, what ContentPackage is, how the pipeline runs, what AWS services are used, how to run tests, how to extend the agent."
argument-hint: "Ask a question about the tech-news-agent project"
---

# tech-news-agent Q&A

## What this skill covers

This skill answers questions about the **tech-news-agent** project — an AWS AgentCore + Amazon Bedrock AI agent that discovers tech news and publishes to configurable output platforms.

Use the reference files below for detailed answers by topic:

| Topic | Reference |
|-------|-----------|
| Architecture, pipeline, AWS services | [Architecture Q&A](./references/architecture-qa.md) |
| Publishers, ContentPackage, adding a platform | [Publishers Q&A](./references/publishers-qa.md) |
| Environment variables, Bedrock model, DynamoDB | [Configuration Q&A](./references/configuration-qa.md) |
| Secrets setup, AWS deploy, CDK, GitHub Actions OIDC | [Deployment Q&A](./references/deployment-qa.md) |
| Tests, linting, local dev, LocalStack | [Development Q&A](./references/development-qa.md) |

---

## Quick answers

**Q: How do I enable LinkedIn posting?**
Set `ENABLED_PUBLISHERS=blog,linkedin` and create the `tech-news-agent/linkedin` secret in AWS Secrets Manager with `{"access_token": "...", "author_urn": "urn:li:person:..."}`. See [Deployment Q&A](./references/deployment-qa.md).

**Q: How do I add a new platform?**
Create `agent/publishers/<platform>.py` subclassing `BasePublisher`, add it to `PUBLISHER_REGISTRY` in `agent/publishers/__init__.py`, add a prompt in `agent/prompts/platforms/`, add a secret name in `agent/config.py`, and write tests. Full checklist: [Publishers Q&A](./references/publishers-qa.md).

**Q: Where are credentials stored?**
**Never in code.** All credentials are stored in AWS Secrets Manager. Secret names are constants in `AgentConfig` (e.g. `AgentConfig.LINKEDIN_SECRET_NAME`). See [Deployment Q&A](./references/deployment-qa.md).

**Q: How do I run the tests?**
```bash
pip install -r requirements-dev.txt
pytest
pytest --cov=agent --cov-report=term-missing  # with coverage
```

**Q: What is a ContentPackage?**
A `ContentPackage` is the platform-agnostic data contract produced by the pipeline after Bedrock summarises the articles. It contains `topic`, `digest`, `articles`, `keywords`, and `raw_post`. Every publisher receives one and formats it for its platform. Defined in `agent/models/__init__.py` (re-exported from `agent/publishers/base.py` for backwards compatibility).

**Q: Which AWS services does this project use?**
AgentCore (agent runtime), EventBridge (scheduling), Bedrock (LLM), DynamoDB (dedup state), Secrets Manager (credentials), CloudWatch (logs/metrics), IAM (least-privilege roles). See [Architecture Q&A](./references/architecture-qa.md).

## Procedure

When asked a project question:
1. Check the Quick answers above first.
2. If more detail is needed, load the relevant reference file.
3. For code-level questions, search the workspace with the actual file names given in the reference.
