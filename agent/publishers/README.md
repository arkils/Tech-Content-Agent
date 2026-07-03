# agent/publishers

This directory contains all **content publisher** implementations.

A publisher is responsible for two things:
1. **Formatting** a platform-agnostic `ContentPackage` into platform-specific text.
2. **Delivering** that text to the target platform (API call, file write, etc.).

## Architecture

```
ContentPackage  (produced by the pipeline)
       │
       ├──► BlogPublisher      → writes Markdown to local filesystem / S3
       ├──► LinkedInPublisher  → LinkedIn Share API
       ├──► InstagramPublisher → Meta Graph API
       └──► YouTubePublisher   → YouTube Data API v3 (Community Posts)
```

The `BasePublisher` abstract class defines the interface.  All publishers
implement `format_content()` and `publish()` independently.

## Adding a new publisher

1. Create a new module, e.g. `tiktok.py`, and subclass `BasePublisher`.
2. Implement `format_content(package)` and `publish(content)`.
3. Register the class in `__init__.py` under `PUBLISHER_REGISTRY`.
4. Add the platform's SSM Parameter Store parameter path to `agent/config.py`.
5. Add a platform-specific prompt in `agent/prompts/platforms/`.
6. Add unit tests in `tests/publishers/`.

## Configuring enabled publishers

Set the `ENABLED_PUBLISHERS` environment variable to a comma-separated list:

```bash
ENABLED_PUBLISHERS=blog,linkedin
ENABLED_PUBLISHERS=instagram,youtube
ENABLED_PUBLISHERS=blog  # default — no credentials required
```

## Platform reference

| Key | Class | Credentials required | API docs |
|-----|-------|----------------------|----------|
| `blog` | `BlogPublisher` | None | — |
| `linkedin` | `LinkedInPublisher` | `/tech-news-agent/linkedin` (SSM Parameter Store) | [LinkedIn Share API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api) |
| `instagram` | `InstagramPublisher` | `/tech-news-agent/instagram` (SSM Parameter Store) | [Meta Graph API](https://developers.facebook.com/docs/instagram-api/guides/content-publishing) |
| `youtube` | `YouTubePublisher` | `/tech-news-agent/youtube` (SSM Parameter Store) | [YouTube Data API v3](https://developers.google.com/youtube/v3/docs/posts/insert) |
