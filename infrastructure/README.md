# infrastructure

This directory contains all **Infrastructure as Code** for the tech-news-agent,
implemented with [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/home.html) (Python).

## Structure

```
infrastructure/
├── app.py              # CDK application entry point
├── stacks/             # CDK stack definitions (one per deployable unit)
└── constructs/         # Reusable L3 CDK constructs
```

## Resources to be provisioned

| Resource | Service | Purpose |
|----------|---------|---------|
| AgentCore Agent | AWS AgentCore | Runs the AI agent |
| Scheduler Rule | Amazon EventBridge | Triggers the agent on a schedule |
| Articles Table | Amazon DynamoDB | Tracks processed articles to prevent duplicates |
| IAM Roles | AWS IAM | Least-privilege execution roles |
| Log Groups | Amazon CloudWatch | Structured agent logs |
| Secrets | AWS SSM Parameter Store | LinkedIn credentials and API keys |

## Prerequisites

- AWS CDK v2 installed: `npm install -g aws-cdk`
- Python dependencies: `pip install -r requirements.txt`
- AWS credentials configured

## TODO

- Implement stack and construct modules.
- Add `cdk.json` for CDK app configuration.
- Document deployment steps in `docs/deployment.md`.
