"""
infrastructure/constructs/__init__.py
======================================
Reusable CDK L3 construct definitions.

Constructs here encapsulate opinionated patterns for resources that appear
in multiple stacks, providing a consistent and secure baseline configuration.

TODO:
    - Add SecureTable construct (DynamoDB with encryption, PITR, deletion protection).
    - Add ObservableFunction construct (Lambda/AgentCore with alarms and dashboards).
    - Add ManagedSecret construct (Secrets Manager with rotation and IAM grants).
"""
