# Architecture Q&A

## Q: What is the high-level architecture of tech-news-agent?

```
EventBridge Scheduler (cron)
        │
        ▼
AWS AgentCore Agent
        │
        ├─ Tool: fetch_tech_news        → News APIs / RSS feeds (external)
        │
        ├─ Tool: check_duplicate        → Amazon DynamoDB (article URL dedup)
        │
        ├─ Tool: summarise_articles     → Amazon Bedrock (Claude)
        │           └─ produces ContentPackage
        │
        └─ Publisher layer
              ├─ BlogPublisher          → local Markdown file / S3
              ├─ LinkedInPublisher      → LinkedIn Share API
              ├─ InstagramPublisher     → Meta Graph API
              └─ YouTubePublisher       → YouTube Data API v3
                      │
                      └─ DynamoDB write (record processed article URLs)
```

Everything is serverless — no EC2 or containers.

---

## Q: What AWS services does this project use and why?

| Service | Role |
|---------|------|
| **AWS AgentCore** | Runs the AI reasoning loop — orchestrates tool calls |
| **Amazon Bedrock** | LLM (Claude) for summarisation and post generation |
| **Amazon EventBridge** | Schedules the agent run (cron-style trigger) |
| **Amazon DynamoDB** | Stores processed article URLs to prevent duplicate posts |
| **AWS Secrets Manager** | Stores all platform credentials at rest, encrypted |
| **Amazon CloudWatch** | Receives structured logs and custom metrics from the pipeline |
| **AWS IAM** | Least-privilege execution roles for the agent |
| **AWS CDK** | Provisions all infrastructure as code |

---

## Q: What is the pipeline flow step by step?

1. EventBridge fires the scheduled rule.
2. AgentCore starts the agent; `agent/main.py` `handler()` is invoked.
3. `NewsPipeline.run()` is called with injected boto3 clients.
4. **Step 1 — Fetch:** `NewsFetcher.run()` reads enabled feed sources from DynamoDB (`tech-news-agent-feeds`), falls back to `AgentConfig.news_feed_urls`, parses RSS feeds via `feedparser`, returns `list[Article]`.
5. **Step 2 — Dedup filter:** `ArticleDeduplicator.filter_new()` batch-checks URLs against DynamoDB (`tech-news-agent-articles`). If empty → early exit with `PipelineResult.skipped = True`.
6. **Step 3 — Summarise:** `ArticleSummariser.run()` sends articles to Bedrock using `agent/prompts/summarize.md`. Returns `list[ArticleSummary]`. If empty → early exit.
7. **Step 4 — Generate post:** `PostGenerator.run(summaries, platform="linkedin")` loads `agent/prompts/platforms/linkedin.md`, renders it, calls Bedrock, returns `ContentPackage`.
8. **Step 5 — Publish:** `get_active_publishers(AgentConfig.enabled_publishers)` instantiates publishers. Each `publisher.run(package)` is called. Failures are isolated — one bad publisher doesn’t stop others.
9. **Step 6 — Mark seen:** `ArticleDeduplicator.mark_seen()` writes processed URLs to DynamoDB with a TTL (default 90 days).
10. `NewsPipeline.run()` returns `PipelineResult` with counts and publish outcomes. `handler()` returns a stats dict to AgentCore.

---

## Q: What is a ContentPackage and where is it defined?

`ContentPackage` is defined in `agent/models/__init__.py` (the canonical location) and
re-exported from `agent/publishers/base.py` for backwards compatibility.

```python
@dataclass
class ContentPackage:
    topic: str           # Headline capturing the day's dominant tech theme
    digest: str          # 2–3 sentence overall digest
    articles: list[ArticleSummary]  # Individual summaries with relevance scores
    keywords: list[str]  # Extracted tech keywords for hashtags / tags
    raw_post: str        # Pre-generated post text from Bedrock
```

Each publisher formats `ContentPackage` independently — the same data produces a different output per platform.

---

## Q: What is ArticleSummary?

Also in `agent/publishers/base.py`:

```python
@dataclass
class ArticleSummary:
    title: str
    url: str
    summary: str          # 2–3 sentence Bedrock summary
    relevance_score: int  # 1–5
    source: str           # Publication name
```

---

## Q: What is PublishResult?

The return value from every publisher's `publish()` method:

```python
@dataclass
class PublishResult:
    platform: str        # e.g. "linkedin"
    success: bool
    post_id: str | None  # Platform-assigned post ID if available
    url: str | None      # Public URL of the published post
    error: str | None    # Error message on failure
```

---

## Q: How does the publisher pattern work?

Every publisher inherits from `BasePublisher` (defined in `agent/publishers/base.py`) and implements two methods:

- `format_content(package: ContentPackage) → str` — transforms the package into platform text.
- `publish(content: str) → PublishResult` — delivers the text to the platform API.

Callers always invoke `publisher.run(package)`, which orchestrates both steps, handles exceptions, and logs the result. Subclasses must not override `run()`.

---

## Q: How are publishers selected at runtime?

Via the `ENABLED_PUBLISHERS` environment variable (read by `AgentConfig`):

```python
# agent/config.py
enabled_publishers: list[str] = _parse_list("ENABLED_PUBLISHERS", "blog")
```

The pipeline calls:
```python
from agent.publishers import get_active_publishers
publishers = get_active_publishers(AgentConfig.enabled_publishers)
# → [BlogPublisher(), LinkedInPublisher()]  for "blog,linkedin"
```

The factory looks up each key in `PUBLISHER_REGISTRY` in `agent/publishers/__init__.py`.

---

## Q: What CDK resources will be provisioned?

Defined as planned stacks in `infrastructure/stacks/README.md`:

| Stack | Resources |
|-------|-----------|
| `TechNewsAgentStack` | AgentCore agent, IAM roles, CloudWatch log groups |
| `SchedulerStack` | EventBridge Scheduler rule targeting the agent |
| `StorageStack` | DynamoDB table `tech-news-agent-articles` |
| `SecretsStack` | Secrets Manager secret stubs + IAM grant policies |

All CDK code lives in `infrastructure/`. Run `cdk synth` to generate CloudFormation.

---

## Q: Where do the Bedrock prompts live?

```
agent/prompts/
├── system.md              # System-level persona prompt (all sessions)
├── summarize.md           # Article batch summarisation prompt
└── platforms/             # Platform-specific post generation prompts
    ├── blog.md
    ├── linkedin.md
    ├── instagram.md
    └── youtube.md
```

Platform prompts include the Bedrock instruction template with `{{PLACEHOLDER}}` variables, format rules, length limits, and output instructions.
