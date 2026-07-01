# News Pipeline Workflow

<!-- TODO: Expand this document once the workflow is implemented. -->

## Overview

The **news pipeline** is the primary workflow of the tech-news-agent.
It is triggered on a schedule by Amazon EventBridge and orchestrates
the following stages:

```
EventBridge trigger
      │
      ▼
1. Fetch tech news              ← tool: fetch_tech_news
      │
      ▼
2. Deduplicate articles         ← tool: check_duplicate  (DynamoDB)
      │
      ▼
3. Summarise articles           ← tool: summarise_articles  (Amazon Bedrock)
      │
      ▼
4. Build ContentPackage         ← models: ArticleSummary, ContentPackage
      │
      ▼
5. Publish to all enabled       ← get_active_publishers(AgentConfig.enabled_publishers)
   platforms in parallel
      │
      ├──► BlogPublisher         → Markdown file / S3
      ├──► LinkedInPublisher     → LinkedIn Share API
      ├──► InstagramPublisher    → Meta Graph API
      └──► YouTubePublisher      → YouTube Data API v3
      │
      ▼
6. Record processed articles    ← DynamoDB write (prevents duplicate posts)
```

## Publisher configuration

Enabled platforms are controlled by the `ENABLED_PUBLISHERS` environment variable.
The pipeline calls `get_active_publishers()` at runtime, so no code changes
are needed to add or remove platforms — only a config change.

## Error handling

TODO: Define per-publisher retry strategy.  A failed publisher should not
block the other publishers — failures are logged and the pipeline continues.

## Observability

TODO: Define CloudWatch metrics emitted at each stage:
- `ArticlesFetched` — count of raw articles retrieved
- `ArticlesAfterDedup` — count after deduplication
- `PublishSuccess` / `PublishFailure` — per platform, per run
