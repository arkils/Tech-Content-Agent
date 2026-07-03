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

## Phase 2 — Agent tools & pipeline ✅ Complete

- [x] `AgentConfig` extended — `news_feeds_table`, `news_feed_urls`, `max_articles_per_run`
- [x] Data models — `FeedSource`, `Article`, `ArticleSummary`, `ContentPackage`, `PublishResult` in `agent/models/`
- [x] `fetch_tech_news` tool — RSS / News API ingestion (DynamoDB feed registry + env var fallback)
- [x] `check_duplicate` tool — DynamoDB article URL deduplication + `mark_seen` write-back with TTL
- [x] `summarise_articles` tool — Amazon Bedrock batch summarisation with duplicate-coverage detection
- [x] `generate_post` tool — LinkedIn post generation via Bedrock; other platforms deferred to Phase 7
- [x] `news_pipeline` workflow — full end-to-end orchestration with early-exit, publisher isolation, and second-run dedup
- [x] Unit test coverage — 168 tests passing

## Phase 3 — Infrastructure ✅ Complete

- [x] Implement `StorageStack` — DynamoDB table (`tech-news-agent-articles`) + feeds table (`tech-news-agent-feeds`)
- [x] Implement `TechNewsAgentStack` — Lambda function + IAM roles + CloudWatch log group
- [x] Implement `SchedulerStack` — EventBridge rule (Mon–Fri 08:00 UTC)
- [x] Implement `SecretsStack` — Secrets Manager stubs + IAM grants
- [x] `cdk synth` verified — all four stacks synthesise cleanly to `cdk.out/`
- [x] Tag all resources with `Project=tech-news-agent`, `ManagedBy=cdk`, `Owner=<context>`
- [x] Local Lambda bundler — no Docker required for synth/deploy

## Phase 4 — Platform API integrations ✅ Complete

- [x] `LinkedInPublisher.publish()` — LinkedIn Share API (`/rest/posts`)
- [x] Secrets Manager credential fetch in `LinkedInPublisher`
- [x] `ENABLE_POSTING` dry-run flag — logs the full post to CloudWatch without calling any API (default: `false`)
- [x] `enable_posting` CDK context parameter — flip to `true` at deploy time to go live
- [x] Infrastructure fixed — `SecretsStack` migrated from SSM to Secrets Manager; Lambda IAM updated to `secretsmanager:GetSecretValue`
- [x] Lambda bundler installs all runtime dependencies (`feedparser`, `requests`)
- [x] 178 unit tests — all passing

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

## Phase 7 — Additional platform integrations

- [ ] `InstagramPublisher.publish()` — Meta Graph API two-step flow
- [ ] `YouTubePublisher.publish()` — YouTube Data API v3 Community Posts
- [ ] Secrets Manager credential fetch in Instagram and YouTube publishers
- [ ] OAuth token refresh handling (Instagram and YouTube tokens expire after 60 days)
- [ ] End-to-end integration tests for Instagram and YouTube
