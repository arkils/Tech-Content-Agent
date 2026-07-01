# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
This project uses [semantic versioning](https://semver.org/) — pre-1.0 while in active initial development.

---

## [Unreleased]

### Planned next
- `fetch_tech_news` tool — RSS / News API ingestion
- `check_duplicate` tool — DynamoDB deduplication
- `summarise_articles` tool — Amazon Bedrock batch summarisation
- `news_pipeline` workflow — end-to-end pipeline wiring
- CDK stack implementations

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
