"""
infrastructure/stacks/__init__.py
==================================
CDK stack definitions package.

Each module in this package defines one CDK stack. Stacks are composed
of one or more CDK constructs and represent a deployable unit of infrastructure.

TODO:
    - Add agent_stack.py  → AgentCore agent, IAM roles, CloudWatch log groups.
    - Add scheduler_stack.py  → EventBridge Scheduler rule.
    - Add storage_stack.py  → DynamoDB table.
    - Add secrets_stack.py  → Secrets Manager resources and IAM permissions.
"""
