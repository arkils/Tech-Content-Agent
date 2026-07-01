# Roadmap

## Phase 1 — Foundation ✅ Complete

- [x] Repository scaffolding and project structure
- [x] CDK infrastructure skeleton (`infrastructure/app.py`, stacks/, constructs/)
- [x] Code quality tooling — Ruff, Black, pytest configured in `pyproject.toml`
- [x] CI/CD pipeline placeholders (GitHub Actions `ci.yml`, `deploy.yml`)
- [x] `BasePublisher` abstraction + `ContentPackage`, `ArticleSummary`, `PublishResult` data contracts
- [x] Publisher registry and factory (`get_active_publishers`, `PUBLISHER_REGISTRY`)
- [x] `BlogPublisher` — fully implemented, writes Markdown, no credentials needed
- [x] `LinkedInPublisher` — `format_content` implemented, `publish` is a placeholder
- [x] `InstagramPublisher` — `format_content` implemented, `publish` is a placeholder
- [x] `YouTubePublisher` — `format_content` implemented, `publish` is a placeholder
- [x] Platform-specific Bedrock prompt templates (`agent/prompts/platforms/`)
- [x] Configurable publisher selection via `ENABLED_PUBLISHERS` env var
- [x] GitHub Copilot instruction files (publishers, tests)
- [x] Project Q&A skill for Copilot (`/project-qa`)
- [x] 39 unit tests — all passing
- [x] Full deployment documentation with secrets setup (`docs/deployment.md`)
- [x] Full development guide (`docs/development.md`)

## Phase 2 — Agent tools & pipeline (next)

- [ ] `fetch_tech_news` tool — RSS / News API ingestion
- [ ] `check_duplicate` tool — DynamoDB article URL deduplication
- [ ] `summarise_articles` tool — Amazon Bedrock batch summarisation
- [ ] `generate_post` tool — per-platform Bedrock post generation using platform prompts
- [ ] `news_pipeline` workflow — wire all tools into an end-to-end pipeline
- [ ] Unit test coverage ≥ 80 %

## Phase 3 — Infrastructure

- [ ] Implement `StorageStack` — DynamoDB table (`tech-news-agent-articles`)
- [ ] Implement `TechNewsAgentStack` — AgentCore agent + IAM roles + CloudWatch log groups
- [ ] Implement `SchedulerStack` — EventBridge Scheduler rule
- [ ] Implement `SecretsStack` — Secrets Manager stubs + IAM grants
- [ ] Deploy all CDK stacks to a dev AWS account
- [ ] Tag all resources with `Project=tech-news-agent` and `Environment=dev`

## Phase 4 — Platform API integrations

- [ ] `LinkedInPublisher.publish()` — LinkedIn Share API (`/rest/posts`)
- [ ] `InstagramPublisher.publish()` — Meta Graph API two-step flow
- [ ] `YouTubePublisher.publish()` — YouTube Data API v3 Community Posts
- [ ] Secrets Manager credential fetch in each publisher
- [ ] OAuth token refresh handling (LinkedIn, Instagram, YouTube all expire after 60 days)
- [ ] End-to-end integration tests per platform

## Phase 5 — Production hardening

- [ ] Dead-letter queue (DLQ) for failed pipeline runs
- [ ] CloudWatch alarms — pipeline failure, no articles fetched, publish errors
- [ ] Per-publisher retry with exponential back-off
- [ ] Rate limiting guards (respect platform API quotas)
- [ ] Cost optimisation review (Bedrock token usage, DynamoDB capacity)
- [ ] Security review — IAM least privilege audit, VPC isolation assessment

## Phase 6 — Observability & Operations

- [ ] CloudWatch dashboard — articles fetched, dedup rate, publish success/failure per platform
- [ ] Automated rollback on CDK deployment failure
- [ ] Runbook documentation (`docs/runbook.md`)
- [ ] Load and chaos testing
