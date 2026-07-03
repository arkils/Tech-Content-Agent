"""
infrastructure/stacks/secrets_stack.py
========================================
SSM Parameter Store SecureString parameters for all platform API credentials.

Parameters are created as encrypted placeholders (value ``"placeholder"``).
Populate each parameter with real credentials via the AWS Console or CLI
before the first pipeline run:

    aws ssm put-parameter \\
        --name "/tech-news-agent/news-api" \\
        --type "SecureString" \\
        --value '{"api_key": "YOUR_KEY"}' \\
        --overwrite

Parameter paths match the constants in ``agent.config.AgentConfig``.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class SecretsStack(cdk.Stack):
    """SSM Parameter Store SecureString stubs for platform API credentials."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Parameters are created with a placeholder value.
        # Replace values via AWS Console or CLI before the first run.
        self.news_api_param = ssm.CfnParameter(
            self,
            "NewsApiParam",
            name="/tech-news-agent/news-api",
            type="SecureString",
            value="placeholder",
            description="NewsAPI.org API key — replace placeholder before first run",
        )

        self.linkedin_param = ssm.CfnParameter(
            self,
            "LinkedInParam",
            name="/tech-news-agent/linkedin",
            type="SecureString",
            value="placeholder",
            description="LinkedIn OAuth access token — replace placeholder before first run",
        )

        self.instagram_param = ssm.CfnParameter(
            self,
            "InstagramParam",
            name="/tech-news-agent/instagram",
            type="SecureString",
            value="placeholder",
            description="Meta Graph API credentials — replace placeholder before first run",
        )

        self.youtube_param = ssm.CfnParameter(
            self,
            "YouTubeParam",
            name="/tech-news-agent/youtube",
            type="SecureString",
            value="placeholder",
            description="YouTube Data API v3 credentials — replace placeholder before first run",
        )
