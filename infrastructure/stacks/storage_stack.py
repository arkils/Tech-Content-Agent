"""
infrastructure/stacks/storage_stack.py
=======================================
DynamoDB tables for article deduplication and feed registry.

Tables
------
- ``tech-news-agent-articles`` — tracks processed article URLs with a TTL
  so records auto-expire after ``article_ttl_days`` (default 90 days).
- ``tech-news-agent-feeds``    — stores the managed RSS/Atom feed registry.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct


class StorageStack(cdk.Stack):
    """DynamoDB storage layer for the tech-news-agent."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------
        # Articles table — deduplication store
        # Partition key: url (String)
        # TTL attribute:  ttl (Number — Unix epoch seconds)
        # ------------------------------------------------------------------
        self.articles_table = dynamodb.Table(
            self,
            "ArticlesTable",
            table_name="tech-news-agent-articles",
            partition_key=dynamodb.Attribute(
                name="url",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
            ),
            time_to_live_attribute="ttl",
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # ------------------------------------------------------------------
        # Feeds table — managed RSS/Atom feed registry
        # Partition key: feed_url (String)
        # ------------------------------------------------------------------
        self.feeds_table = dynamodb.Table(
            self,
            "FeedsTable",
            table_name="tech-news-agent-feeds",
            partition_key=dynamodb.Attribute(
                name="feed_url",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        cdk.CfnOutput(self, "ArticlesTableName", value=self.articles_table.table_name)
        cdk.CfnOutput(self, "FeedsTableName", value=self.feeds_table.table_name)
