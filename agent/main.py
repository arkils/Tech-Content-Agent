"""
agent/main.py
=============
Entry point for the tech-news-agent.

This module is invoked by AWS AgentCore when the agent is triggered by
an EventBridge scheduled event.  It initialises AWS clients, runs the
news pipeline workflow, and returns a structured response.

TODO:
    - Implement AgentCore handler interface contract (response schema).
    - Add structured logging via CloudWatch.
"""

import logging

import boto3

from agent.config import AgentConfig
from agent.workflows.news_pipeline import NewsPipeline

logger = logging.getLogger(__name__)


def handler(event: dict, context: object) -> dict:
    """
    AWS AgentCore / Lambda entry point.

    Args:
        event: The triggering event payload (e.g. EventBridge scheduled event).
        context: The Lambda/AgentCore runtime context object.

    Returns:
        A response dict with pipeline run statistics.
    """
    logger.info("tech-news-agent started", extra={"event": event})

    dynamodb_client = boto3.client("dynamodb", region_name=AgentConfig.aws_region)
    bedrock_client = boto3.client("bedrock-runtime", region_name=AgentConfig.aws_region)

    pipeline = NewsPipeline(
        dynamodb_client=dynamodb_client,
        bedrock_client=bedrock_client,
    )

    result = pipeline.run()

    return {
        "status": "skipped" if result.skipped else "ok",
        "articles_fetched": result.articles_fetched,
        "articles_new": result.articles_new,
        "summaries_produced": result.summaries_produced,
        "publishers_succeeded": sum(1 for r in result.publish_results if r.success),
        "publishers_total": len(result.publish_results),
        "skip_reason": result.skip_reason or None,
    }
