# infrastructure/stacks

This directory contains AWS CDK **stack** definitions.

A stack is a unit of deployment in AWS CDK. Each stack maps to a
CloudFormation stack and can be deployed or destroyed independently.

## Planned stacks

| Module | Stack | Resources |
|--------|-------|-----------|
| `agent_stack.py` | `TechNewsAgentStack` | AgentCore agent, IAM roles, CloudWatch log groups |
| `scheduler_stack.py` | `SchedulerStack` | EventBridge Scheduler rule and target |
| `storage_stack.py` | `StorageStack` | DynamoDB table for processed articles |
| `secrets_stack.py` | `SecretsStack` | Secrets Manager secrets and IAM grant policies |

## TODO

- Implement each stack module.
- Add cross-stack references where resources are shared.
- Tag all resources with `Project=tech-news-agent` and `Environment=<env>`.
