"""
infrastructure/stacks/secrets_stack.py
========================================
SSM Parameter Store SecureString parameters for all platform API credentials.

Parameters are created with placeholder values.  Populate each parameter with
real credentials via the AWS Console or CLI before the first pipeline run:

    aws ssm put-parameter \\
        --name "/tech-news-agent/linkedin" \\
        --type SecureString \\
        --value '{"access_token": "YOUR_TOKEN", "author_urn": "urn:li:person:YOUR_ID"}' \\
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

        # Parameters are created with placeholder JSON matching the expected schema.
        # Replace values via AWS Console or CLI before the first run.
        self.news_api_param = ssm.StringParameter(
            self,
            "NewsApiParam",
            parameter_name="/tech-news-agent/news-api",
            description="NewsAPI.org API key — replace placeholder before first run",
            string_value='{"api_key": "placeholder"}',
        )

        self.linkedin_param = ssm.StringParameter(
            self,
            "LinkedInParam",
            parameter_name="/tech-news-agent/linkedin",
            description="LinkedIn OAuth credentials — replace placeholder before first run",
            string_value='{"access_token": "placeholder", "author_urn": "placeholder"}',
        )

        self.instagram_param = ssm.StringParameter(
            self,
            "InstagramParam",
            parameter_name="/tech-news-agent/instagram",
            description="Meta Graph API credentials — replace placeholder before first run",
            string_value='{"access_token": "placeholder", "instagram_account_id": "placeholder"}',
        )

        self.youtube_param = ssm.StringParameter(
            self,
            "YouTubeParam",
            parameter_name="/tech-news-agent/youtube",
            description="YouTube Data API v3 credentials — replace placeholder before first run",
            string_value='{"client_id": "placeholder", "client_secret": "placeholder", "refresh_token": "placeholder"}',
        )
