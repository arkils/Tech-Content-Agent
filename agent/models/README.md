# agent/models

This directory contains data model definitions used across the agent.

Models define the **contracts** between tools and workflows, ensuring type
safety and enabling automatic validation and serialisation.

## Planned models

| Model | Description |
|-------|-------------|
| `Article` | A raw news article fetched from a source |
| `ArticleSummary` | A Bedrock-generated summary of an article |
| `LinkedInPost` | A fully composed LinkedIn post ready for publishing |
| `AgentResponse` | The top-level response returned to AgentCore |

## TODO

- Implement all model classes.
- Add JSON schema export for AgentCore tool definitions.
- Add field-level validation rules.
