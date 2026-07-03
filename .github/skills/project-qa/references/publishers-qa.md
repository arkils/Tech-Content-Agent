# Publishers Q&A

## Q: What publishers currently exist?

| Key | Class | File | Status |
|-----|-------|------|--------|
| `blog` | `BlogPublisher` | `agent/publishers/blog.py` | ✅ Fully implemented |
| `linkedin` | `LinkedInPublisher` | `agent/publishers/linkedin.py` | 🔧 `format_content` done, `publish` is a placeholder |
| `instagram` | `InstagramPublisher` | `agent/publishers/instagram.py` | 🔧 `format_content` done, `publish` is a placeholder |
| `youtube` | `YouTubePublisher` | `agent/publishers/youtube.py` | 🔧 `format_content` done, `publish` is a placeholder |

`blog` is the default — it writes Markdown files to disk and requires no credentials.

---

## Q: How do I add a brand new publisher (e.g. Hashnode, Dev.to, TikTok)?

Follow this checklist:

### 1. Create the publisher module

File: `agent/publishers/<platform>.py`

```python
"""
agent/publishers/<platform>.py
================================
<Platform> content publisher.

Expected SSM Parameter Store JSON:
    {"key": "value"}

TODO: implement _get_credentials() and publish()
"""
from __future__ import annotations
import logging
from agent.publishers.base import BasePublisher, ContentPackage, PublishResult

logger = logging.getLogger(__name__)

class <Platform>Publisher(BasePublisher):
    platform_name = "<platform_key>"

    def format_content(self, package: ContentPackage) -> str:
        # TODO: call Bedrock with agent/prompts/platforms/<platform>.md
        return package.raw_post  # placeholder

    def publish(self, content: str) -> PublishResult:
        # TODO: fetch credentials, call API
        raise NotImplementedError("<Platform>Publisher.publish() not yet implemented")
```

### 2. Register the publisher

In `agent/publishers/__init__.py`, add:
```python
from agent.publishers.<platform> import <Platform>Publisher

PUBLISHER_REGISTRY: dict[str, type[BasePublisher]] = {
    ...,
    "<platform_key>": <Platform>Publisher,
}
```

### 3. Add the parameter path to config

In `agent/config.py`, inside `AgentConfig`:
```python
<PLATFORM>_PARAM_PATH: str = "/tech-news-agent/<platform>"
```

### 4. Add the Bedrock prompt

Create `agent/prompts/platforms/<platform>.md` with:
- Audience description
- The Bedrock prompt template with `{{PLACEHOLDER}}` variables
- Format rules and length limits

### 5. Write tests

Create `tests/publishers/test_<platform>.py` — see the test template in
`.github/instructions/tests.instructions.md`.

Minimum tests:
- `format_content()` returns a non-empty string
- `format_content()` does not exceed the platform character limit
- `publish()` raises `NotImplementedError` (until implemented)

### 6. Update `agent/publishers/README.md`

Add a row to the platform table.

### 7. Create the AWS parameter

```bash
aws ssm put-parameter \
    --name "/tech-news-agent/<platform>" \
    --description "<Platform> credentials for tech-news-agent" \
    --type SecureString \
    --value '{"key": "value"}'
```

### 8. Enable it

```bash
export ENABLED_PUBLISHERS=blog,<platform_key>
```

---

## Q: How does BlogPublisher work?

`BlogPublisher` is the only fully implemented publisher. It:

1. `format_content()` — builds a Markdown string with YAML front-matter:
   ```yaml
   ---
   title: "..."
   date: "2026-01-01T..."
   tags: ["aws", "python"]
   draft: false
   ---
   ```
   Then appends `digest`, `raw_post`, and a Sources section with article links.

2. `publish()` — writes the Markdown to `output_dir` (from `AgentConfig.blog_output_path`).
   Filename format: `YYYY-MM-DD-<uuid8>.md`.
   Creates the directory if it doesn't exist.
   Returns `PublishResult(success=True, url=<file_path>)`.

The output directory defaults to `output/posts` (set via `BLOG_OUTPUT_PATH` env var).

---

## Q: How does LinkedInPublisher format content?

`format_content()` in `LinkedInPublisher`:
1. Takes `package.raw_post` as the base text.
2. Builds hashtags from the first 5 keywords: `#aws #python #ai ...`
3. Appends hashtags after the post text.
4. Truncates to 3,000 characters (LinkedIn's limit) with `...` if needed.

`publish()` is **not yet implemented** — it raises `NotImplementedError`.
The TODO in the file describes what's needed: SSM Parameter Store fetch → LinkedIn Share API POST.

---

## Q: What is the character limit for each platform?

| Platform | Limit | Where enforced |
|----------|-------|----------------|
| LinkedIn | 3,000 chars | `_MAX_CHARS` in `linkedin.py` |
| Instagram | 2,200 chars | `_MAX_CAPTION_CHARS` in `instagram.py` |
| YouTube Community Post | 5,000 chars | `_MAX_POST_CHARS` in `youtube.py` |
| Blog (Markdown) | No hard limit | — |

---

## Q: How does `get_active_publishers()` work?

```python
# agent/publishers/__init__.py
def get_active_publishers(enabled: list[str]) -> list[BasePublisher]:
    unknown = [k for k in enabled if k not in PUBLISHER_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown publisher(s): {unknown}...")
    return [PUBLISHER_REGISTRY[key]() for key in enabled]
```

- Raises `ValueError` immediately if any key is unknown (fail fast).
- Preserves the order of `enabled`.
- Instantiates a fresh publisher object per key.

---

## Q: How do I implement credential fetching in a publisher?

Inject the boto3 client via constructor so tests can mock it:

```python
def __init__(self, ssm_client=None):
    import boto3
    self._ssm = ssm_client or boto3.client(
        "ssm", region_name=AgentConfig.aws_region
    )

def _get_credentials(self) -> dict:
    import json
    response = self._ssm.get_parameter(
        Name=AgentConfig.LINKEDIN_PARAM_PATH, WithDecryption=True
    )
    return json.loads(response["Parameter"]["Value"])
```

Then in `publish()`:
```python
def publish(self, content: str) -> PublishResult:
    creds = self._get_credentials()
    # use creds["access_token"], creds["author_urn"], etc.
    ...
```

Never cache credentials — fetch fresh on each invocation.
Never log credential values — log only success or failure.

---

## Q: Where are the publisher tests?

```
tests/publishers/
├── __init__.py
├── test_registry.py     # PUBLISHER_REGISTRY completeness + get_active_publishers()
├── test_blog.py         # Full BlogPublisher tests (format + publish + run)
├── test_linkedin.py     # format_content + NotImplementedError for publish
├── test_instagram.py    # format_content + NotImplementedError for publish
└── test_youtube.py      # format_content + NotImplementedError for publish
```

Run publisher tests only:
```bash
pytest tests/publishers/ -v
```
