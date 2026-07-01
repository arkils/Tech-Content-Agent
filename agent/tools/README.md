# agent/tools

This directory contains the AgentCore **tool** implementations used by the agent.

Each tool is a discrete, testable unit of functionality that the agent can invoke
during its reasoning loop.

## Planned tools

| Module | Tool name | Description |
|--------|-----------|-------------|
| `news_fetcher.py` | `fetch_tech_news` | Retrieves articles from RSS feeds and News APIs |
| `deduplication.py` | `check_duplicate` | Queries DynamoDB to detect previously processed articles |
| `bedrock_summariser.py` | `summarise_articles` | Calls Amazon Bedrock to summarise a batch of articles |
| `linkedin_publisher.py` | `publish_linkedin_post` | Publishes a post via the LinkedIn API |

## Tool contract

Every tool must:

1. Accept a well-typed input model.
2. Return a well-typed output model.
3. Raise descriptive exceptions on failure.
4. Be independently unit-testable with mocked AWS clients.

## TODO

- Implement each tool module.
- Add input/output Pydantic models in `agent/models/`.
- Register tools with AgentCore.
