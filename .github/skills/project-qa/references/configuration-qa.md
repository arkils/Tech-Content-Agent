# Configuration Q&A

## Q: What environment variables does the project use?

All non-sensitive configuration is read from environment variables in `agent/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region for all SDK calls |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Bedrock model for summarisation and post generation |
| `DYNAMODB_TABLE_NAME` | `tech-news-agent-articles` | DynamoDB table tracking processed article URLs (dedup) |
| `NEWS_FEEDS_TABLE` | `tech-news-agent-feeds` | DynamoDB table for the managed RSS feed registry |
| `NEWS_FEED_URLS` | *(5 hardcoded defaults)* | Comma-separated fallback RSS URLs when DynamoDB feed table is empty |
| `MAX_ARTICLES_PER_RUN` | `20` | Max articles to process per run (Bedrock cost cap) |
| `ARTICLE_TTL_DAYS` | `90` | Days before processed article records expire in DynamoDB |
| `LOG_LEVEL` | `INFO` | Python logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `ENABLED_PUBLISHERS` | `blog` | Comma-separated platform keys to publish to |
| `BLOG_OUTPUT_PATH` | `output/posts` | Directory where BlogPublisher writes Markdown files |

Default RSS feed sources (used when `NEWS_FEED_URLS` is unset and DynamoDB is empty):
- Ars Technica Technology Lab
- The Verge
- TechCrunch
- AWS Blog
- Hacker News

Example:
```bash
export AWS_REGION=us-east-1
export ENABLED_PUBLISHERS=blog,linkedin
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
export DYNAMODB_TABLE_NAME=tech-news-agent-articles
export NEWS_FEEDS_TABLE=tech-news-agent-feeds
export MAX_ARTICLES_PER_RUN=20
export ARTICLE_TTL_DAYS=90
export LOG_LEVEL=DEBUG
export BLOG_OUTPUT_PATH=output/posts
```

---

## Q: How do I change which platforms are published to?

Set `ENABLED_PUBLISHERS` to a comma-separated list of platform keys:

```bash
# Default — blog only, no credentials needed
ENABLED_PUBLISHERS=blog

# LinkedIn and blog
ENABLED_PUBLISHERS=blog,linkedin

# All platforms
ENABLED_PUBLISHERS=blog,linkedin,instagram,youtube

# Instagram only
ENABLED_PUBLISHERS=instagram
```

Valid keys: `blog`, `linkedin`, `instagram`, `youtube`

The agent reads this at startup via `AgentConfig.enabled_publishers` (a `list[str]`).
If an unknown key is passed, `get_active_publishers()` raises `ValueError` immediately.

---

## Q: How do I change the Bedrock model?

Set the `BEDROCK_MODEL_ID` environment variable:

```bash
# Claude 3.5 Sonnet (default)
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Claude 3 Haiku (cheaper, faster)
export BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Claude 3 Opus (most capable)
export BEDROCK_MODEL_ID=anthropic.claude-3-opus-20240229-v1:0
```

Bedrock models must be enabled in your AWS account / region.
Activate them in the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess).

---

## Q: What are the SSM Parameter Store parameter paths?

Defined as constants in `AgentConfig` — these are paths, never values:

| Constant | Parameter path | Purpose |
|----------|----------------|--------|
| `AgentConfig.NEWS_API_PARAM_PATH` | `/tech-news-agent/news-api` | News API key |
| `AgentConfig.LINKEDIN_PARAM_PATH` | `/tech-news-agent/linkedin` | LinkedIn access token + author URN |
| `AgentConfig.INSTAGRAM_PARAM_PATH` | `/tech-news-agent/instagram` | Instagram access token + account ID |
| `AgentConfig.YOUTUBE_PARAM_PATH` | `/tech-news-agent/youtube` | Google OAuth2 credentials + channel ID |

---

## Q: Where is the DynamoDB table name configured?

Via the `DYNAMODB_TABLE_NAME` environment variable.
Default: `tech-news-agent-articles`.

This table stores processed article URLs to prevent the agent from posting about the same article twice. The CDK `StorageStack` will provision this table.

---

## Q: How does AgentConfig parse list environment variables?

Via the `_parse_list` helper in `agent/config.py`:

```python
def _parse_list(env_var: str, default: str) -> list[str]:
    raw = os.environ.get(env_var, default)
    return [item.strip() for item in raw.split(",") if item.strip()]
```

This means trailing spaces, extra commas, and empty items are all safely ignored:
- `"blog, linkedin"` → `["blog", "linkedin"]`  ✅
- `"blog,,linkedin"` → `["blog", "linkedin"]`  ✅
- `"  blog  "` → `["blog"]`  ✅

---

## Q: How do I add a new configuration value?

For **non-sensitive** values, add a class attribute to `AgentConfig` in `agent/config.py`:

```python
class AgentConfig:
    my_new_setting: str = os.environ.get("MY_NEW_SETTING", "default_value")
    my_int_setting: int = int(os.environ.get("MY_INT_SETTING", "10"))
```

For **sensitive** values (credentials, tokens, keys):
- Add a `PARAM_PATH` constant: `MY_PLATFORM_PARAM_PATH: str = "/tech-news-agent/my-platform"`
- Create the parameter in AWS SSM Parameter Store (SecureString).
- Fetch the value at runtime with `boto3`.
- **Never** store the actual value in code or environment variables.

---

## Q: What is the default publisher and why?

The default is `blog` (set by `ENABLED_PUBLISHERS=blog` default in `AgentConfig`).

**Why `blog`?**
- `BlogPublisher` writes Markdown files to the local filesystem.
- It requires **no external credentials** — safe to run in any environment.
- It's the easiest way to verify the pipeline is working end-to-end before connecting real APIs.
- Generated files can later be served by GitHub Pages, Hugo, Docusaurus, or uploaded to S3.
