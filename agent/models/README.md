# agent/models

This directory contains all data model definitions used across the agent.

Models define the **contracts** between tools and workflows.
All models are plain `@dataclass` — no external dependencies.

## Implemented models

| Model | Defined in | Created by | Consumed by |
|-------|-----------|------------|-------------|
| `FeedSource` | `__init__.py` | `NewsFetcher` (DynamoDB or config) | `NewsFetcher._parse_feed()` |
| `Article` | `__init__.py` | `NewsFetcher` | `ArticleDeduplicator`, `ArticleSummariser` |
| `ArticleSummary` | `__init__.py` | `ArticleSummariser` | `PostGenerator`, publishers |
| `ContentPackage` | `__init__.py` | `PostGenerator` | All publishers via `publisher.run()` |
| `PublishResult` | `__init__.py` | Each publisher's `publish()` | `NewsPipeline` result aggregation |

## Backwards compatibility

`agent/publishers/base.py` re-exports `ArticleSummary`, `ContentPackage`, and
`PublishResult` from here — existing imports of those names from `base.py` continue to work.

## Data flow

```
FeedSource  →  Article[]  →  ArticleSummary[]  →  ContentPackage  →  PublishResult[]
   (RSS)       (fetched)      (Bedrock)           (per-run bundle)   (per-publisher)
```
