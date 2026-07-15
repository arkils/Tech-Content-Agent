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
- [x] SSM Parameter Store credential fetch in `LinkedInPublisher` (SecureString, KMS-encrypted)
- [x] `ENABLE_POSTING` dry-run flag — logs the full post to CloudWatch without calling any API (default: `false`)
- [x] `enable_posting` CDK context parameter — flip to `true` at deploy time to go live
- [x] Infrastructure: `SecretsStack` uses SSM Parameter Store SecureString; Lambda IAM grants `ssm:GetParameter` on `arn:aws:ssm:*:*:parameter/tech-news-agent/*`
- [x] Lambda bundler installs all runtime dependencies (`feedparser`, `requests`)
- [x] 180 unit tests — all passing

## Phase 4.1 — Post Tracking, LLM Provider Switch & Developer Experience ✅ Complete

- [x] **Post tracking** — new `PostTracker` tool writes every publish attempt to a dedicated `tech-news-agent-posts` DynamoDB table; status progresses `pending` → `success | dry_run | error`
- [x] **`dry_run` status** — when `ENABLE_POSTING=false` the post is generated and stored with `status=dry_run` (not `success`) so the audit trail is accurate
- [x] **LLM provider switch** — `LLM_PROVIDER=openai` routes both summarisation and post-generation directly to OpenAI Chat Completions, bypassing Bedrock entirely; `LLM_PROVIDER=bedrock` (default) keeps the existing Bedrock-first + OpenAI-fallback behaviour
- [x] **Configurable OpenAI model** — `OPENAI_MODEL_ID` env var (default `gpt-4.1-mini`) used instead of a hardcoded model name
- [x] **CloudWatch logging fix** — `logging.getLogger().setLevel()` applied in `handler()` so INFO-level pipeline logs actually reach CloudWatch
- [x] **LinkedIn-only default** — `ENABLED_PUBLISHERS` now defaults to `linkedin`; `output/posts/` added to `.gitignore`
- [x] **Local runner** — `scripts/run_local.py` loads `.env.local`, prints a config summary, and runs the full pipeline against real AWS; `--dry-run` and `--force-new` flags for safe local iteration
- [x] **`.env.example`** — committed template documenting every env var with descriptions and defaults
- [x] 192 unit tests — all passing

## Phase 4.2 — Deduplication window, prompt refinement & API maintenance ✅ Complete

- [x] **Deduplication recent-seen window** — `ArticleDeduplicator._fetch_existing_urls()` now checks `processed_at` timestamp; only articles seen within the past 24 hours are treated as duplicates — older DynamoDB records are retained for history but no longer suppress re-fetching
- [x] **LinkedIn API version bump** — `_LINKEDIN_API_VERSION` updated from `202504` to `202506` to stay aligned with LinkedIn's versioned REST API
- [x] **Local runner refactor** — `scripts/run_local.py` instantiates `AgentConfig()` at runtime so env-var overrides (e.g. `--force-new`) are reflected correctly in the printed config summary
- [x] **LinkedIn post prompt refinement** — `agent/prompts/platforms/linkedin.md` rewritten for tighter structure, stronger call-to-action, and clearer tone guidance
- [x] 194 unit tests — all passing

## Phase 5 — Human-in-the-Loop (HITL) Approval

Full detail: [`docs/hitl-plan.md`](hitl-plan.md)

- [ ] `ApprovalStatus` enum + `ApprovalRecord` dataclass in `agent/models/`
- [ ] `AgentConfig` — `HITL_ENABLED`, `APPROVALS_TABLE_NAME`, FCM + secret SSM paths
- [ ] `agent/tools/approval_store.py` — DynamoDB CRUD for approvals table (TTL 24 h)
- [ ] `agent/tools/push_notifier.py` — FCM HTTP v1 push notifications via SSM-stored service account
- [ ] `agent/workflows/news_pipeline.py` — HITL gate: when `HITL_ENABLED=true`, store approval record + push instead of publishing directly
- [ ] `agent/handlers/approval_api.py` — Lambda Function URL handler (GET / approve / reject / device-token update)
- [ ] `agent/handlers/publish_handler.py` — async-invoked Lambda that calls `LinkedInPublisher.publish()`
- [ ] `infrastructure/stacks/approval_stack.py` — approvals DynamoDB table, two Lambdas, Function URLs, IAM grants
- [ ] Infrastructure updates — `storage_stack.py`, `agent_stack.py`, `app.py`
- [ ] Android app (`android/`) — Kotlin, FCM, Retrofit, review / edit / confirm / reject UI
- [ ] Unit tests for all new backend components
- [ ] `HITL_ENABLED=false` default — existing pipeline behaviour fully preserved

## Phase 6 — Production hardening

- [ ] Dead-letter queue (DLQ) for failed pipeline runs
- [ ] CloudWatch alarms — pipeline failure, no articles fetched, publish errors
- [ ] Per-publisher retry with exponential back-off
- [ ] Rate limiting guards (respect platform API quotas)
- [ ] Cost optimisation review (Bedrock token usage, DynamoDB capacity)
- [ ] Security review — IAM least privilege audit, VPC isolation assessment

## Phase 7 — Observability & Operations

- [ ] CloudWatch dashboard — articles fetched, dedup rate, publish success/failure per platform
- [ ] Automated rollback on CDK deployment failure
- [ ] Runbook documentation (`docs/runbook.md`)
- [ ] Load and chaos testing

## Phase 8 — Additional platform integrations

- [ ] `InstagramPublisher.publish()` — Meta Graph API two-step flow
- [ ] `YouTubePublisher.publish()` — YouTube Data API v3 Community Posts
- [ ] Secrets Manager credential fetch in Instagram and YouTube publishers
- [ ] OAuth token refresh handling (Instagram and YouTube tokens expire after 60 days)
- [ ] End-to-end integration tests for Instagram and YouTube
