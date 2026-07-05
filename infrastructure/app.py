"""
infrastructure/app.py
=====================
AWS CDK application entry point for tech-news-agent.

Usage
-----
    # Synth (dry-run)
    cdk synth

    # Deploy all stacks
    cdk deploy --all -c owner=<your-name>

    # Destroy all stacks
    cdk destroy --all

Context parameters
------------------
``owner``
    Value for the ``Owner`` resource tag.  Pass via ``-c owner=<value>``
    or set in ``cdk.json`` under ``context.owner``.
"""

from __future__ import annotations

import aws_cdk as cdk

from stacks.agent_stack import TechNewsAgentStack
from stacks.scheduler_stack import SchedulerStack
from stacks.secrets_stack import SecretsStack
from stacks.storage_stack import StorageStack

app = cdk.App()

# ---------------------------------------------------------------------------
# Tags applied to every resource in every stack.
# Pass -c owner=<your-name> at deploy time, or set context.owner in cdk.json.
# ---------------------------------------------------------------------------
owner: str = app.node.try_get_context("owner") or "unset"
enabled_publishers: str = app.node.try_get_context("enabled_publishers") or "linkedin"
enable_posting: bool = app.node.try_get_context("enable_posting") == "true"
bedrock_model_id: str = app.node.try_get_context("bedrock_model_id") or "amazon.nova-lite-v1:0"
llm_provider: str = app.node.try_get_context("llm_provider") or "bedrock"
openai_model_id: str = app.node.try_get_context("openai_model_id") or "gpt-4.1-mini"
force_no_new_articles: bool = app.node.try_get_context("force_no_new_articles") == "true"
cdk.Tags.of(app).add("Project", "tech-news-agent")
cdk.Tags.of(app).add("ManagedBy", "cdk")
cdk.Tags.of(app).add("Owner", owner)

# ---------------------------------------------------------------------------
# Stacks
# ---------------------------------------------------------------------------
storage = StorageStack(app, "TechNewsAgentStorage")
secrets = SecretsStack(app, "TechNewsAgentSecrets")

agent = TechNewsAgentStack(
    app,
    "TechNewsAgent",
    articles_table=storage.articles_table,
    feeds_table=storage.feeds_table,
    posts_table=storage.posts_table,
    enabled_publishers=enabled_publishers,
    enable_posting=enable_posting,
    bedrock_model_id=bedrock_model_id,
    llm_provider=llm_provider,
    openai_model_id=openai_model_id,
    force_no_new_articles=force_no_new_articles,
)

scheduler = SchedulerStack(
    app,
    "TechNewsAgentScheduler",
    agent_function=agent.function,
)

app.synth()
