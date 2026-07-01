# agent/workflows

This directory contains workflow orchestration logic for the tech-news-agent.

A **workflow** composes multiple tools into a coherent, multi-step pipeline.

## Workflows

| Module | Description |
|--------|-------------|
| `news_pipeline.py` | End-to-end pipeline: fetch → deduplicate → summarise → publish |

## TODO

- Implement `news_pipeline.py`.
- Add workflow-level error handling and retry policies.
- Emit CloudWatch metrics at each pipeline stage.
