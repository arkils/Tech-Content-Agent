# Deployment Guide

Step-by-step instructions for provisioning the tech-news-agent infrastructure
in your AWS account and configuring all required secrets.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [One-time AWS account bootstrap](#2-one-time-aws-account-bootstrap)
3. [Configure credentials in Secrets Manager](#3-configure-credentials-in-secrets-manager)
4. [Configure environment variables](#4-configure-environment-variables)
5. [Deploy the infrastructure](#5-deploy-the-infrastructure)
6. [Verify the deployment](#6-verify-the-deployment)
7. [Update an existing deployment](#7-update-an-existing-deployment)
8. [Teardown](#8-teardown)

---

## 1. Prerequisites

Install the following tools before deploying:

| Tool | Version | Install command |
|------|---------|---------------|
| Python | 3.9+ | [python.org](https://www.python.org/downloads/) — macOS: `brew install python` |
| AWS CLI | v2 | [aws.amazon.com/cli](https://aws.amazon.com/cli/) — macOS: `brew install awscli` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) — macOS: `brew install node` |
| AWS CDK CLI | v2 | `npm install -g aws-cdk` |

> **Note:** Docker is **not required**. The Lambda asset is bundled locally
> using a built-in pip-based bundler.

Verify your tools:

```bash
python --version      # 3.9 or higher (use python3 on macOS if python is not found)
aws --version         # aws-cli/2.x.x
node --version        # v18.x.x or higher
cdk --version         # 2.x.x
```

Create and activate a virtual environment, then install dependencies:

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# Then install dependencies (all platforms)
pip install -r requirements.txt
```

> **macOS note:** Always create the venv with `python3`. Once the venv is
> activated, `python` and `pip` point to the venv's interpreter automatically.

Configure the AWS CLI with credentials for your target account:

```bash
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name: us-east-1
# Default output format: json
```

> **Tip:** For a personal account, long-lived IAM user access keys are the
> simplest option. For shared/CI environments, use an IAM role with OIDC.

---

## 2. One-time AWS account bootstrap

CDK must be bootstrapped **once per AWS account / region** before the first deploy.
This creates the `CDKToolkit` CloudFormation stack, an S3 bucket for Lambda assets,
and the IAM roles CDK needs to deploy.

```bash
cdk bootstrap -c owner=<your-name>
```

To bootstrap a specific account/region explicitly:

```bash
cdk bootstrap aws://<YOUR_ACCOUNT_ID>/us-east-1 -c owner=<your-name>
```

---

## 3. Configure credentials in Secrets Manager

Platform credentials are stored as **AWS Secrets Manager** secrets —
encrypted at rest with KMS and fetched at runtime by the Lambda.

**Never store actual credential values in code, config files, or environment variables.**

The secret names are defined as constants in `agent/config.py`.
CDK creates each secret with a placeholder JSON value — you must replace each
value before the first run.

### 3a. News API key

Required — the agent uses this to fetch tech news articles.

```bash
aws secretsmanager put-secret-value \
    --secret-id "/tech-news-agent/news-api" \
    --secret-string '{"api_key": "YOUR_NEWS_API_KEY_HERE"}'
```

Expected JSON structure:
```json
{ "api_key": "<your-newsapi.org-or-similar-api-key>" }
```

### 3b. LinkedIn credentials

Required only when `linkedin` is in `ENABLED_PUBLISHERS`.

Obtain credentials from the [LinkedIn Developer Portal](https://www.linkedin.com/developers/):
1. Create a LinkedIn App.
2. Request the `w_member_social` product (Share on LinkedIn).
3. Generate a long-lived OAuth 2.0 access token.
4. Note your person URN (`urn:li:person:<id>`) from the `/v2/me` API.

```bash
aws secretsmanager put-secret-value \
    --secret-id "/tech-news-agent/linkedin" \
    --secret-string '{"access_token": "YOUR_TOKEN", "author_urn": "urn:li:person:YOUR_ID"}'
```

Expected JSON structure:
```json
{
    "access_token": "<oauth2-access-token>",
    "author_urn":   "urn:li:person:<person-id>"
}
```

> **Note:** LinkedIn access tokens expire after 60 days — regenerate manually before expiry.

### 3c. Instagram credentials

Required only when `instagram` is in `ENABLED_PUBLISHERS`.

Obtain credentials from the [Meta for Developers portal](https://developers.facebook.com/):
1. Create a Meta App with Instagram Graph API access.
2. Connect an Instagram Business or Creator account.
3. Generate a long-lived User Access Token with `instagram_basic` and `instagram_content_publish` permissions.
4. Note your Instagram User ID.

```bash
aws secretsmanager put-secret-value \
    --secret-id "/tech-news-agent/instagram" \
    --secret-string '{"access_token": "YOUR_TOKEN", "instagram_account_id": "YOUR_ID"}'
```

Expected JSON structure:
```json
{
    "access_token":        "<long-lived-user-access-token>",
    "instagram_account_id": "<ig-user-id>"
}
```

> **Note:** Long-lived tokens expire after 60 days — refresh via `/refresh_access_token` before expiry.

### 3d. YouTube credentials

Required only when `youtube` is in `ENABLED_PUBLISHERS`.

Obtain credentials from [Google Cloud Console](https://console.cloud.google.com/):
1. Create a project and enable the YouTube Data API v3.
2. Create an OAuth 2.0 Client ID (Desktop or Web App type).
3. Run the OAuth flow once locally to obtain a refresh token.

```bash
aws secretsmanager put-secret-value \
    --secret-id "/tech-news-agent/youtube" \
    --secret-string '{"client_id":"ID","client_secret":"SECRET","refresh_token":"TOKEN","channel_id":"CHANNEL"}'
```

Expected JSON structure:
```json
{
    "client_id":     "<oauth2-client-id>",
    "client_secret": "<oauth2-client-secret>",
    "refresh_token": "<oauth2-refresh-token>",
    "channel_id":    "<youtube-channel-id>"
}
```

### Verify secrets are in place

```bash
# List all tech-news-agent secrets (names only, values hidden)
aws secretsmanager list-secrets \
    --filters Key=name,Values=/tech-news-agent \
    --query "SecretList[].Name"
```

---

## 4. Configure environment variables

Non-sensitive configuration is passed via environment variables.
For the CDK deploy step, export these in your shell or CI environment:

```bash
# Required
export AWS_REGION=us-east-1

# Which platforms to publish to (comma-separated, no spaces)
# Valid keys: blog, linkedin, instagram, youtube
export ENABLED_PUBLISHERS=blog,linkedin

# Bedrock model (default is Claude 3.5 Sonnet)
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# DynamoDB table name (must match what CDK provisions)
export DYNAMODB_TABLE_NAME=tech-news-agent-articles

# For BlogPublisher — local path where Markdown files are written
export BLOG_OUTPUT_PATH=output/posts
```

> **`ENABLE_POSTING`** is intentionally **not** set here — it is controlled via
> a CDK context flag at deploy time (see Section 5) so it cannot accidentally
> be left on in a shell environment.

---

## 5. Deploy the infrastructure

```bash
# 1. Synthesise the CloudFormation templates (dry-run, no AWS calls)
cdk synth -c owner=<your-name>

# 2. Review what will be created
cdk diff -c owner=<your-name>

# 3. Deploy (posting disabled — posts logged to CloudWatch only)
cdk deploy --all -c owner=<your-name>

# 4. Deploy with live posting enabled
cdk deploy --all -c owner=<your-name> -c enable_posting=true

# Or deploy a single stack
cdk deploy TechNewsAgentStorage -c owner=<your-name>
```

> **Tip:** Start with `enable_posting` unset (defaults to `false`) to verify
> CloudWatch logs look correct before enabling live posts.

CDK will display a summary of IAM changes and prompt for confirmation
before creating any resources.

### What gets deployed

| Stack | Resource | Purpose |
|-------|----------|---------| 
| `TechNewsAgentStorage` | DynamoDB `tech-news-agent-articles` | Article deduplication with TTL |
| `TechNewsAgentStorage` | DynamoDB `tech-news-agent-feeds` | Managed RSS feed registry |
| `TechNewsAgentSecrets` | Secrets Manager × 4 | Platform credential stubs |
| `TechNewsAgent` | Lambda `tech-news-agent` | Pipeline handler (15 min, 512 MB) |
| `TechNewsAgent` | IAM execution role | Least-privilege access to DynamoDB, Bedrock, Secrets Manager |
| `TechNewsAgent` | CloudWatch log group `/aws/lambda/tech-news-agent` | Structured logs (30-day retention) |
| `TechNewsAgentScheduler` | EventBridge rule `tech-news-agent-daily` | Mon–Fri trigger at 08:00 UTC |

### Resource tags applied to every resource

| Tag | Value |
|-----|-------|
| `Project` | `tech-news-agent` |
| `ManagedBy` | `cdk` |
| `Owner` | value of `-c owner=<your-name>` |

---

## 6. Verify the deployment

After a successful deploy, run a quick smoke test:

```bash
# Check the Lambda function exists
aws lambda get-function --function-name tech-news-agent --query 'Configuration.State'

# Check the log group exists
aws logs describe-log-groups \
    --log-group-name-prefix /aws/lambda/tech-news-agent

# Check the DynamoDB articles table is ACTIVE
aws dynamodb describe-table \
    --table-name tech-news-agent-articles \
    --query "Table.TableStatus"

# Manually invoke the Lambda (after populating secrets)
aws lambda invoke \
    --function-name tech-news-agent \
    --payload '{}' \
    response.json
cat response.json
```

---

## 7. Update an existing deployment

After making code or infrastructure changes:

```bash
# Review what will change
cdk diff -c owner=<your-name>

# Apply changes
cdk deploy --all -c owner=<your-name>
```

CDK performs a CloudFormation change-set — only changed resources are updated.

### Updating a secret value

```bash
aws secretsmanager put-secret-value \
    --secret-id "tech-news-agent/linkedin" \
    --secret-string '{"access_token": "NEW_TOKEN", "author_urn": "urn:li:person:ID"}'
```

The agent fetches secrets at runtime, so no re-deploy is needed after
updating a secret value.

---

## 8. Teardown

```bash
# Destroy all provisioned resources
cdk destroy --all
```

> **Warning:** This deletes the DynamoDB table and all stored article history.
> Export the table data first if you want to preserve it:
>
> ```bash
> aws dynamodb scan --table-name tech-news-agent-articles > articles-backup.json
> ```

### Delete secrets manually (CDK does not manage secrets by default)

```bash
aws secretsmanager delete-secret --secret-id "tech-news-agent/news-api" --recovery-window-in-days 7
aws secretsmanager delete-secret --secret-id "tech-news-agent/linkedin" --recovery-window-in-days 7
aws secretsmanager delete-secret --secret-id "tech-news-agent/instagram" --recovery-window-in-days 7
aws secretsmanager delete-secret --secret-id "tech-news-agent/youtube" --recovery-window-in-days 7
```

---

## GitHub Actions deployment

The [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) workflow
automates CDK deployment on merge to `main`.

It uses **GitHub OIDC** — no static AWS credentials are stored as GitHub Secrets.

### Setting up OIDC (one-time)

1. In your AWS account, create an IAM OIDC identity provider for GitHub:

```bash
aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"
```

2. Create an IAM role that GitHub Actions can assume, with a trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      },
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:<YOUR_ORG>/tech-news-agent:*"
      }
    }
  }]
}
```

3. Attach CDK deployment permissions to the role.

4. Add the role ARN as a GitHub repository variable named `AWS_DEPLOY_ROLE_ARN`.

5. Add your AWS account ID and region as repository variables:
   - `AWS_ACCOUNT_ID`
   - `AWS_REGION`
