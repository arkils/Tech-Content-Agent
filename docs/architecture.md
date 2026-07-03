# Architecture

<!-- TODO: Replace this placeholder with a full architecture diagram and description. -->

## Overview

`tech-news-agent` is a fully serverless, event-driven AI agent built on
**AWS AgentCore** and **Amazon Bedrock**.

## High-level diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                              │
│                                                                 │
│  EventBridge Scheduler                                          │
│        │  (scheduled trigger)                                   │
│        ▼                                                        │
│  AWS AgentCore Agent                                            │
│        │                                                        │
│        ├──► fetch_tech_news ──► News APIs / RSS Feeds           │
│        │                                                        │
│        ├──► check_duplicate ──► Amazon DynamoDB                 │
│        │                                                        │
│        ├──► summarise_articles ──► Amazon Bedrock               │
│        │                                                        │
│        ├──► generate_linkedin_post ──► Amazon Bedrock           │
│        │                                                        │
│        └──► publish_linkedin_post ──► LinkedIn API              │
│                                                                 │
│  Amazon CloudWatch (logs, metrics, alarms)                      │
│  AWS SSM Parameter Store (LinkedIn credentials, News API keys)  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Service | Description |
|-----------|---------|-------------|
| Scheduler | Amazon EventBridge | Triggers the agent on a configurable cron schedule |
| Agent runtime | AWS AgentCore | Manages the reasoning loop and tool invocations |
| Summarisation | Amazon Bedrock | LLM-based article summarisation |
| Post generation | Amazon Bedrock | LLM-based LinkedIn post creation |
| State store | Amazon DynamoDB | Tracks processed article URLs |
| Secrets | AWS SSM Parameter Store | Stores API credentials at rest, encrypted (SecureString) |
| Observability | Amazon CloudWatch | Logs, metrics, and alarms |

## TODO

- Add a formal architecture diagram (e.g. draw.io or Mermaid).
- Document data flow and message contracts between components.
- Document IAM trust policies and permission boundaries.
- Document disaster recovery and data retention policies.
