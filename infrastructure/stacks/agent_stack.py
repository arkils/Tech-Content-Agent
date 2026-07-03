"""
infrastructure/stacks/agent_stack.py
======================================
Lambda function, IAM execution role, and CloudWatch log group for the
tech-news-agent.

Bundling
--------
CDK first attempts **local bundling** (no Docker required):

1. ``feedparser`` is pip-installed into the asset output directory.
2. The ``agent/`` package is copied from the project root.

If local bundling fails, CDK falls back to the AWS SAM Python 3.12 Docker
image using the same steps.  Docker is only needed as a fallback.

IAM grants
----------
- DynamoDB read/write on the articles table.
- DynamoDB read-only on the feeds table.
- ``bedrock:InvokeModel`` on the configured Claude model.
- ``ssm:GetParameter`` on all ``/tech-news-agent/*`` parameters.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import aws_cdk as cdk
import jsii
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct

# Resolve the project root (two levels up from this file: stacks/ -> infrastructure/ -> root).
_PROJECT_ROOT = Path(__file__).parent.parent.parent


@jsii.implements(cdk.ILocalBundling)
class _LocalBundler:
    """Bundles the Lambda asset locally without requiring Docker."""

    def try_bundle(self, output_dir: str, *, options: cdk.BundlingOptions | None = None) -> bool:
        try:
            subprocess.run(
                ["pip", "install", "feedparser", "requests", "-t", output_dir, "--quiet"],
                check=True,
            )
            shutil.copytree(
                str(_PROJECT_ROOT / "agent"),
                str(Path(output_dir) / "agent"),
            )
            return True
        except Exception:
            return False


class TechNewsAgentStack(cdk.Stack):
    """Lambda function and supporting resources for the tech-news-agent."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        articles_table: dynamodb.Table,
        feeds_table: dynamodb.Table,
        enabled_publishers: str = "blog,linkedin",
        enable_posting: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        log_group = logs.LogGroup(
            self,
            "AgentLogGroup",
            log_group_name="/aws/lambda/tech-news-agent",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        self.function = lambda_.Function(
            self,
            "AgentFunction",
            function_name="tech-news-agent",
            description="Fetches tech news, summarises it, and publishes to enabled platforms.",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="agent.main.handler",
            code=lambda_.Code.from_asset(
                str(_PROJECT_ROOT),
                bundling=cdk.BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    local=_LocalBundler(),
                    command=[
                        "bash",
                        "-c",
                        (
                            "pip install feedparser requests -t /asset-output --quiet"
                            " && cp -r /asset-input/agent /asset-output/agent"
                        ),
                    ],
                ),
            ),
            timeout=cdk.Duration.minutes(15),
            memory_size=512,
            log_group=log_group,
            environment={
                "DYNAMODB_TABLE_NAME": articles_table.table_name,
                "NEWS_FEEDS_TABLE": feeds_table.table_name,
                "ENABLED_PUBLISHERS": enabled_publishers,
                "ENABLE_POSTING": "true" if enable_posting else "false",
                "LOG_LEVEL": "INFO",
            },
        )

        # ------------------------------------------------------------------
        # IAM grants
        # ------------------------------------------------------------------
        articles_table.grant_read_write_data(self.function)
        feeds_table.grant_read_data(self.function)

        self.function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockInvokeModel",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[
                    "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
                ],
            )
        )

        self.function.add_to_role_policy(
            iam.PolicyStatement(
                sid="SSMGetParameter",
                effect=iam.Effect.ALLOW,
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/tech-news-agent/*"
                ],
            )
        )

        cdk.CfnOutput(self, "AgentFunctionArn", value=self.function.function_arn)
