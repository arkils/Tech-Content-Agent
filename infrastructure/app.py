"""
infrastructure/app.py
=====================
AWS CDK application entry point for tech-news-agent.

This file bootstraps the CDK app and instantiates all stacks.
Run `cdk deploy` from this directory to provision infrastructure.

TODO:
    - Instantiate TechNewsAgentStack once implemented.
    - Add environment-specific configuration (dev / staging / prod).
    - Add stack tagging for cost allocation and ownership.

Usage:
    cdk synth
    cdk deploy
    cdk destroy
"""

import aws_cdk as cdk

# TODO: import stacks once implemented
# from stacks.agent_stack import TechNewsAgentStack

app = cdk.App()

# TODO: instantiate stacks
# TechNewsAgentStack(app, "TechNewsAgentStack", ...)

app.synth()
