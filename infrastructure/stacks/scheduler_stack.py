"""
infrastructure/stacks/scheduler_stack.py
==========================================
EventBridge Scheduler rule that triggers the tech-news-agent Lambda
Monday–Friday at 08:00 UTC.

Adjust the cron expression to change the schedule without touching any
other stack.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as lambda_
from constructs import Construct


class SchedulerStack(cdk.Stack):
    """EventBridge rule that triggers the agent on a recurring schedule."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        agent_function: lambda_.Function,
        **kwargs: object,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        rule = events.Rule(
            self,
            "DailyTrigger",
            rule_name="tech-news-agent-daily",
            description="Triggers tech-news-agent Monday–Friday at 08:00 UTC",
            schedule=events.Schedule.cron(
                minute="0",
                hour="8",
                month="*",
                week_day="MON-FRI",
                year="*",
            ),
        )

        rule.add_target(targets.LambdaFunction(agent_function))

        cdk.CfnOutput(self, "ScheduleRuleArn", value=rule.rule_arn)
