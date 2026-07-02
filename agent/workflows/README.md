# agent/workflows

This directory contains workflow orchestration logic for the tech-news-agent.

A **workflow** composes multiple tools into a coherent, multi-step pipeline.

## Implemented workflows (Phase 2)

| Module | Class | Description |
|--------|-------|-------------|
| `news_pipeline.py` | `NewsPipeline` | Full end-to-end pipeline triggered by EventBridge |

## `NewsPipeline` — step-by-step

```
Step 1  NewsFetcher.run()                    → list[Article]      (RSS ingestion)
Step 2  ArticleDeduplicator.filter_new()     → list[Article]      (DynamoDB dedup — early exit if empty)
Step 3  ArticleSummariser.run()              → list[ArticleSummary] (Bedrock — early exit if empty)
Step 4  PostGenerator.run(platform)          → ContentPackage     (Bedrock post generation)
Step 5  get_active_publishers() → publisher.run(package) × N     (fan-out to all enabled platforms)
Step 6  ArticleDeduplicator.mark_seen()                           (write URLs to DynamoDB with TTL)
```

## `PipelineResult`

Returned by `NewsPipeline.run()` — never raises:

```python
@dataclass
class PipelineResult:
    articles_fetched: int          # raw count from RSS
    articles_new: int              # count after dedup
    summaries_produced: int        # count from Bedrock
    publish_results: list[PublishResult]  # one per enabled publisher
    skipped: bool                  # True on early exit
    skip_reason: str               # human-readable reason when skipped
```

## Error handling

- A failed publisher does **not** stop the pipeline — error is captured in `PublishResult.error`.
- DynamoDB errors in `filter_new()` propagate (hard stop — better safe than re-publishing).
- Bedrock errors propagate from the summariser and generator.

## TODO (Phase 5)

- Add per-publisher retry with exponential back-off.
- Emit CloudWatch metrics at each step (`ArticlesFetched`, `ArticlesAfterDedup`, `PublishSuccess`/`PublishFailure`).
