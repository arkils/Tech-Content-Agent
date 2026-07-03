"""
infrastructure/stacks/secrets_stack.py
========================================
AWS Secrets Manager secrets for all platform API credentials.

Secrets are created with placeholder values.  Populate each secret with
real credentials via the AWS Console or CLI before the first pipeline run:

    aws secretsmanager put-secret-value \\
        --secret-id "/tech-news-agent/linkedin" \\
        --secret-string '{"access_token": "YOUR_TOKEN", "author_urn": "urn:li:person:YOUR_ID"}'

Secret names match the constants in ``agent.config.AgentConfig``.
"""

from __future__ import annotations

import aws_cdk as cdk
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class SecretsStack(cdk.Stack):
    """Secrets Manager secret stubs for platform API credentials."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs: object) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Secrets are created with placeholder JSON matching the expected schema.
        # Replace values via AWS Console or CLI before the first run.
        self.news_api_secret = secretsmanager.CfnSecret(
            self,
            "NewsApiSecret",
            name="/tech-news-agent/news-api",
            description="NewsAPI.org API key — replace placeholder before first run",
            secret_string='{"api_key": "placeholder"}',
        )

        self.linkedin_secret = secretsmanager.CfnSecret(
            self,
            "LinkedInSecret",
            name="/tech-news-agent/linkedin",
            description="LinkedIn OAuth credentials — replace placeholder before first run",
            secret_string='{"access_token": "placeholder", "author_urn": "placeholder"}',
        )

        self.instagram_secret = secretsmanager.CfnSecret(
            self,
            "InstagramSecret",
            name="/tech-news-agent/instagram",
            description="Meta Graph API credentials — replace placeholder before first run",
            secret_string='{"access_token": "placeholder", "instagram_account_id": "placeholder"}',
        )

        self.youtube_secret = secretsmanager.CfnSecret(
            self,
            "YouTubeSecret",
            name="/tech-news-agent/youtube",
            description="YouTube Data API v3 credentials — replace placeholder before first run",
            secret_string='{"client_id": "placeholder", "client_secret": "placeholder", "refresh_token": "placeholder"}',
        )
