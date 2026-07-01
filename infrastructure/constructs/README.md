# infrastructure/constructs

This directory contains reusable AWS CDK **L3 construct** definitions.

L3 constructs encapsulate opinionated, reusable patterns built on top of
lower-level CDK L1/L2 constructs.

## Planned constructs

| Module | Construct | Description |
|--------|-----------|-------------|
| `secure_table.py` | `SecureTable` | DynamoDB table with encryption, PITR, and deletion protection |
| `observable_agent.py` | `ObservableAgent` | AgentCore agent with CloudWatch alarms and dashboards |
| `managed_secret.py` | `ManagedSecret` | Secrets Manager secret with rotation and least-privilege IAM grants |

## TODO

- Implement each construct module.
- Add unit tests for constructs using `aws_cdk.assertions`.
