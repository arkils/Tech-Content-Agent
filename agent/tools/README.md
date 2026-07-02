# agent/tools

This directory contains the AgentCore **tool** implementations used by the agent.

Each tool is a discrete, testable unit of functionality that the agent can invoke
during its reasoning loop.  All tools accept injected boto3 clients for testability.

## Implemented tools (Phase 2)

| Module | Class | Input | Output | Description |
|--------|-------|-------|--------|-------------|
| `news_fetcher.py` | `NewsFetcher` | — | `list[Article]` | RSS ingestion; DynamoDB feed registry with env var fallback |
| `deduplication.py` | `ArticleDeduplicator` | `list[Article]` | `list[Article]` | URL dedup via DynamoDB `BatchGetItem`; `mark_seen()` writes with TTL |
| `bedrock_summariser.py` | `ArticleSummariser` | `list[Article]` | `list[ArticleSummary]` | Bedrock batch summarisation; drops model-flagged duplicates |
| `post_generator.py` | `PostGenerator` | `list[ArticleSummary]` | `ContentPackage` | Platform post generation via Bedrock; LinkedIn only (Phase 2) |

## Tool contract

Every tool must:

1. Accept injected boto3 clients via `__init__` — never create them internally.
2. Accept a well-typed input model from `agent/models/`.
3. Return a well-typed output model from `agent/models/`.
4. Raise descriptive exceptions on failure — never swallow silently.
5. Be independently unit-testable with mocked AWS clients.

## Feed registry (news_fetcher)

`NewsFetcher` resolves feed sources using a **hybrid strategy**:
1. Scans the DynamoDB `news_feeds_table` (`tech-news-agent-feeds`) for `enabled = true` records.
2. Falls back to `AgentConfig.news_feed_urls` if the table is empty or unreachable.

Feed record schema (partition key `feed_url`):
```json
{"feed_url": "https://...", "name": "Ars Technica", "category": "general", "enabled": true}
```

## Deduplication TTL

Article records in `tech-news-agent-articles` expire after `AgentConfig.article_ttl_days`
(default 90 days) via DynamoDB TTL — no manual cleanup needed.
