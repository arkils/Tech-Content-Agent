# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
This project uses [semantic versioning](https://semver.org/) — pre-1.0 while in active initial development.

---

## [Unreleased]

### Planned next
- CDK stack implementations (Phase 3)

---

## [0.9.0] — 2026-07-02

### Added
- **`agent/workflows/news_pipeline.py`** — `NewsPipeline` end-to-end orchestration:
  - Step 1: fetch articles via `NewsFetcher`
  - Step 2: filter with `ArticleDeduplicator.filter_new()`
  - Step 3: summarise via `ArticleSummariser` (Bedrock)
  - Step 4: generate LinkedIn post via `PostGenerator` (Bedrock)
  - Step 5: fan-out to all enabled publishers
  - Step 6: record processed URLs via `ArticleDeduplicator.mark_seen()`
  - Early-exit with `PipelineResult.skipped` when no new articles or no summaries
  - Publisher failures isolated — one failed publisher never blocks others
- **`tests/test_news_pipeline.py`** — 13 integration-style tests covering happy-path, both early-exit conditions, publisher failure resilience, and second-run deduplication
- **`agent/main.py`** — fully implemented `handler()` entry point; creates boto3 clients and runs `NewsPipeline`; returns structured stats dict
- **`tests/test_agent.py`** — replaced `NotImplementedError` placeholder test with 5 tests covering response shape and status values

---

## [0.8.0] — 2026-07-02

### Added
- **`agent/tools/post_generator.py`** — `PostGenerator` tool (LinkedIn only for Phase 2):
  - Loads the platform-specific Bedrock prompt template from `agent/prompts/platforms/`
  - Extracts the prompt text from markdown code fences automatically
  - Derives `topic` (highest-relevance article title), `keywords` (from titles), and `digest` (first sentence of top article)
  - Calls Bedrock `converse` and returns a fully populated `ContentPackage`
  - Raises `ValueError` for unsupported platforms — blog, instagram, youtube deferred to Phase 4
- **`tests/test_post_generator.py`** — 27 unit tests covering run, prompt rendering, Bedrock call, error paths, and all helper functions

### Notes
- Other platforms (blog, instagram, youtube) will be added to `PostGenerator` in Phase 4 alongside their `publish()` implementations

---

## [0.7.0] — 2026-07-02

### Added
- **`agent/tools/bedrock_summariser.py`** — `ArticleSummariser` tool:
  - Renders the `agent/prompts/summarize.md` template with the article batch
  - Calls Bedrock `converse` API (model configurable via `AgentConfig.bedrock_model_id`)
  - Parses structured JSON response into `ArticleSummary` objects
  - Drops articles flagged by the model as duplicate coverage
  - Handles JSON in markdown fences, inline arrays, or prose-wrapped responses
  - Skips incomplete items rather than raising
- **`tests/test_bedrock_summariser.py`** — 20 unit tests covering run, JSON extraction edge cases, prompt rendering, and error paths

---

## [0.6.0] — 2026-07-02

### Added
- **`agent/tools/deduplication.py`** — `ArticleDeduplicator` tool:
  - `filter_new(articles)` — batch-checks URLs against DynamoDB, returns only unseen articles
  - `mark_seen(articles)` — writes processed URLs to DynamoDB with TTL for automatic expiry
  - Handles batches >100 items (DynamoDB `BatchGetItem` limit) and >25 items (`BatchWriteItem` limit) transparently
- **`tests/test_deduplication.py`** — 18 unit tests including a full round-trip test and large-batch (120 item) coverage
- **`AgentConfig.article_ttl_days`** — configurable DynamoDB TTL (default 90 days, overridable via `ARTICLE_TTL_DAYS` env var)

---

## [0.5.0] — 2026-07-02

### Added
- **`agent/tools/news_fetcher.py`** — `NewsFetcher` tool implementing the hybrid feed-source strategy:
  - Queries DynamoDB `news_feeds_table` for enabled `FeedSource` records
  - Falls back to `AgentConfig.news_feed_urls` when the table is empty or unreachable
  - Parses RSS/Atom feeds with `feedparser`, extracts `Article` objects
  - Deduplicates by URL within a batch and caps output at `max_articles_per_run`
  - Gracefully skips failed feeds and continues with the rest
- **`tests/test_news_fetcher.py`** — 23 unit tests covering DynamoDB resolution, RSS parsing, dedup, cap, and all helper functions
- **`feedparser>=6.0`** added to `requirements.txt`

---

## [0.4.0] — 2026-07-02

### Added
- **`agent/models/__init__.py`** — canonical data model definitions for all inter-module contracts:
  - `FeedSource` — news feed record loaded from DynamoDB or the fallback URL list; includes `from_url()` factory
  - `Article` — raw fetched article (url, title, source, published_at, content)
  - `ArticleSummary` — Bedrock-summarised article (moved here from `publishers/base.py`)
  - `ContentPackage` — platform-agnostic bundle passed to every publisher (moved here)
  - `PublishResult` — publisher delivery outcome (moved here)
- **`tests/test_models.py`** — 15 unit tests covering all five models and backwards-compatibility imports
- **`agent/config.py`** — three new configuration fields for Phase 2:
  - `news_feeds_table` — DynamoDB table name for the managed feed registry (`tech-news-agent-feeds`)
  - `news_feed_urls` — fallback RSS feed list (5 defaults; overridable via `NEWS_FEED_URLS` env var)
  - `max_articles_per_run` — Bedrock cost cap, defaults to 20 (overridable via `MAX_ARTICLES_PER_RUN`)
- **`tests/test_config.py`** — expanded from 2 to 11 tests covering all config fields

### Changed
- `agent/publishers/base.py` — `ArticleSummary`, `ContentPackage`, and `PublishResult` are now imported from `agent/models` and re-exported for backwards compatibility; dataclass definitions removed from this file
- `agent/config.py` — module docstring expanded with hybrid feed-source strategy documentation

---

## [0.3.0] — 2026-07-01

### Added
- **Deployment documentation** (`docs/deployment.md`) — fully rewritten with:
  - Step-by-step CDK bootstrap and deploy sequence
  - All four platform secrets with exact JSON shapes and where to obtain credentials
  - GitHub OIDC setup instructions (no static AWS credentials in CI)
  - Secret rotation and teardown procedures
- **Development guide** (`docs/development.md`) — expanded with:
  - LocalStack offline development setup
  - AWS mocking patterns with `moto`
  - Running the agent locally via `BlogPublisher`
  - Full branch and PR strategy

### Changed
- Roadmap updated to reflect completed Phase 1 and accurately planned Phases 2–6
- Phase 3 renamed from "LinkedIn Integration" to "Platform API integrations" to reflect multi-platform design

---

## [0.2.0] — 2026-07-01

### Added
- **Multi-platform publisher layer** — configurable output platforms replacing the LinkedIn-only design
  - `agent/publishers/base.py` — `BasePublisher` abstract class, `ContentPackage`, `ArticleSummary`, `PublishResult` data contracts
  - `agent/publishers/blog.py` — `BlogPublisher` (fully implemented, writes Markdown to disk, no credentials required)
  - `agent/publishers/linkedin.py` — `LinkedInPublisher` (`format_content` + 3,000-char truncation; `publish` placeholder)
  - `agent/publishers/instagram.py` — `InstagramPublisher` (`format_content` + 2,200-char truncation; `publish` placeholder)
  - `agent/publishers/youtube.py` — `YouTubePublisher` (`format_content` + 5,000-char limit + source links; `publish` placeholder)
  - `agent/publishers/__init__.py` — `PUBLISHER_REGISTRY` + `get_active_publishers()` factory
- **Platform-specific Bedrock prompt templates** (`agent/prompts/platforms/`)
  - `linkedin.md` — professional, 150–300 words, hashtags, no bullet points
  - `instagram.md` — punchy hook ≤ 125 chars, emoji paragraphs, 15–25 hashtags
  - `youtube.md` — conversational community post, source links, subscriber CTA
  - `blog.md` — structured Markdown, 600–1,200 words, front-matter aware
- **Configurable publisher selection** via `ENABLED_PUBLISHERS` environment variable (comma-separated)
- **`AgentConfig` extended** with `enabled_publishers`, `blog_output_path`, and per-platform `*_SECRET_NAME` constants (`INSTAGRAM_SECRET_NAME`, `YOUTUBE_SECRET_NAME`)
- **GitHub Copilot instruction files**
  - `.github/instructions/publishers.instructions.md` — step-by-step guide for implementing a new publisher (applies to `agent/publishers/**`)
  - `.github/instructions/tests.instructions.md` — test conventions and templates (applies to `tests/**`)
- **Publisher tests** — 39 unit tests, all passing
  - `tests/publishers/test_registry.py` — registry completeness + `get_active_publishers` factory
  - `tests/publishers/test_blog.py` — full `BlogPublisher` (format, publish, run, edge cases)
  - `tests/publishers/test_linkedin.py` — `LinkedInPublisher` format + truncation
  - `tests/publishers/test_instagram.py` — `InstagramPublisher` format + truncation
  - `tests/publishers/test_youtube.py` — `YouTubePublisher` format + source links
- **`agent/publishers/README.md`** — platform table, architecture diagram, add-a-publisher guide

### Changed
- `agent/config.py` — added publisher configuration section; `ENABLED_PUBLISHERS` defaults to `blog`
- `agent/prompts/linkedin.md` — superseded by `agent/prompts/platforms/linkedin.md`
- `agent/workflows/news_pipeline.md` — updated pipeline diagram to show multi-platform publisher fan-out
- `README.md` — updated overview, project structure tree, and added publisher configuration table

---

## [0.1.0] — 2026-07-01

### Added
- **Repository scaffold** — initial project structure
- `agent/__init__.py`, `agent/main.py`, `agent/config.py` — entry point and configuration
- `agent/models/`, `agent/tools/`, `agent/workflows/` — package stubs with READMEs
- `agent/prompts/system.md`, `agent/prompts/summarize.md` — base Bedrock prompt templates
- `agent/workflows/news_pipeline.md` — pipeline stage diagram
- `infrastructure/app.py` — CDK application entry point
- `infrastructure/stacks/`, `infrastructure/constructs/` — placeholder CDK packages
- `infrastructure/README.md` — planned resources table
- `cdk.json` — CDK app configuration with recommended feature flags
- `tests/conftest.py`, `tests/test_agent.py`, `tests/test_config.py` — initial test suite
- `pyproject.toml` — Ruff, Black, and pytest configured (line length 100, Python 3.13 target)
- `requirements.txt`, `requirements-dev.txt`
- `.gitignore` — covers Python, CDK, AWS credentials, IDE files, secrets
- `.github/workflows/ci.yml`, `.github/workflows/deploy.yml` — CI/CD placeholders
- `.github/copilot-instructions.md` — repo-wide Copilot context
- `docs/architecture.md`, `docs/deployment.md`, `docs/development.md`, `docs/roadmap.md`
- `scripts/README.md`

---

## [0.2.1] — 2026-07-01

### Added
- **Project Q&A Copilot skill** (`.github/skills/project-qa/`) — invoke with `/project-qa` or natural language questions
  - `SKILL.md` — entry point with quick answers and reference index
  - `references/architecture-qa.md` — pipeline flow, AWS services, data contracts
  - `references/publishers-qa.md` — publisher pattern, adding platforms, credential patterns
  - `references/configuration-qa.md` — all environment variables, secret names, defaults
  - `references/deployment-qa.md` — CDK bootstrap, secrets setup, OIDC, teardown
  - `references/development-qa.md` — local setup, tests, linting, LocalStack, conventions
