# Deployment Q&A

## Q: What are the prerequisites before deploying?

| Tool | Minimum version | Check |
|------|----------------|-------|
| Python | 3.13 | `python --version` |
| AWS CLI | v2 | `aws --version` |
| Node.js | 18 | `node --version` |
| AWS CDK CLI | v2 | `cdk --version` |

Install CDK CLI:
```bash
npm install -g aws-cdk
```

Configure AWS credentials:
```bash
aws configure
# AWS Access Key ID: <your key>
# AWS Secret Access Key: <your secret>
# Default region: us-east-1
```

---

## Q: What is CDK bootstrap and do I need to run it?

Yes — once per AWS account / region. It creates the `CDKToolkit` stack with an S3 bucket and IAM roles that CDK needs to deploy.

```bash
cdk bootstrap aws://<YOUR_ACCOUNT_ID>/us-east-1

# Or auto-detect account and region
cdk bootstrap
```

You only need to run this once. If someone on your team already bootstrapped the account/region, skip this step.

---

## Q: What is the full deploy sequence?

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Synthesise CloudFormation templates (validates your CDK code)
cdk synth

# 3. Preview what will be created / changed
cdk diff

# 4. Deploy all stacks
cdk deploy --all
```

CDK will show IAM changes and prompt for confirmation before creating resources.

---

## Q: How do I create the secrets in AWS Secrets Manager?

Run these commands — **replace placeholder values with your real credentials**.

### News API (required)
```bash
aws secretsmanager create-secret \
    --name "tech-news-agent/news-api" \
    --description "News API key for tech-news-agent" \
    --region us-east-1

aws secretsmanager put-secret-value \
    --secret-id "tech-news-agent/news-api" \
    --secret-string '{"api_key": "YOUR_API_KEY_HERE"}'
```

### LinkedIn (required only if `linkedin` is enabled)
```bash
aws secretsmanager create-secret \
    --name "tech-news-agent/linkedin" \
    --description "LinkedIn API credentials" \
    --region us-east-1

aws secretsmanager put-secret-value \
    --secret-id "tech-news-agent/linkedin" \
    --secret-string '{
        "access_token": "YOUR_LINKEDIN_ACCESS_TOKEN",
        "author_urn": "urn:li:person:YOUR_PERSON_ID"
    }'
```
Get credentials from: [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
Token expires: every 60 days.

### Instagram (required only if `instagram` is enabled)
```bash
aws secretsmanager create-secret \
    --name "tech-news-agent/instagram" \
    --description "Instagram Graph API credentials" \
    --region us-east-1

aws secretsmanager put-secret-value \
    --secret-id "tech-news-agent/instagram" \
    --secret-string '{
        "access_token": "YOUR_INSTAGRAM_ACCESS_TOKEN",
        "instagram_account_id": "YOUR_IG_USER_ID"
    }'
```
Get credentials from: [Meta for Developers](https://developers.facebook.com/)
Token expires: every 60 days — refresh via `/refresh_access_token` endpoint.

### YouTube (required only if `youtube` is enabled)
```bash
aws secretsmanager create-secret \
    --name "tech-news-agent/youtube" \
    --description "YouTube Data API credentials" \
    --region us-east-1

aws secretsmanager put-secret-value \
    --secret-id "tech-news-agent/youtube" \
    --secret-string '{
        "client_id": "YOUR_GOOGLE_CLIENT_ID",
        "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
        "refresh_token": "YOUR_OAUTH2_REFRESH_TOKEN",
        "channel_id": "YOUR_YOUTUBE_CHANNEL_ID"
    }'
```
Get credentials from: [Google Cloud Console](https://console.cloud.google.com/) → YouTube Data API v3.

---

## Q: How do I verify my secrets are set correctly?

```bash
# List all tech-news-agent secrets
aws secretsmanager list-secrets \
    --filter Key=name,Values=tech-news-agent \
    --query "SecretList[].Name"

# Verify a secret exists without revealing the value
aws secretsmanager describe-secret --secret-id "tech-news-agent/linkedin"

# Check the value (careful — this shows the actual secret in your terminal)
aws secretsmanager get-secret-value \
    --secret-id "tech-news-agent/linkedin" \
    --query SecretString \
    --output text
```

---

## Q: How do I update a secret value (e.g. rotate a LinkedIn token)?

```bash
aws secretsmanager put-secret-value \
    --secret-id "tech-news-agent/linkedin" \
    --secret-string '{
        "access_token": "NEW_TOKEN",
        "author_urn": "urn:li:person:YOUR_ID"
    }'
```

The agent fetches secrets at runtime on every invocation — no re-deploy needed.

---

## Q: How do I deploy without storing AWS credentials in GitHub?

Use **GitHub OIDC** — the recommended approach. No static credentials are stored.

One-time setup:

**1. Create the OIDC provider in AWS:**
```bash
aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"
```

**2. Create an IAM role with this trust policy** (replace `<ACCOUNT_ID>` and `<YOUR_ORG>`):
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

**3. Attach CDK deploy permissions to the role.**

**4. Add these as GitHub repository variables** (not secrets — they are not sensitive):
- `AWS_DEPLOY_ROLE_ARN` — the ARN of the role above
- `AWS_ACCOUNT_ID`
- `AWS_REGION`

The `.github/workflows/deploy.yml` workflow uses these variables to assume the role via OIDC.

---

## Q: How do I tear down all the infrastructure?

```bash
# Destroy all CDK stacks
cdk destroy --all
```

> **Warning:** This deletes the DynamoDB table. Export data first:
> ```bash
> aws dynamodb scan --table-name tech-news-agent-articles > backup.json
> ```

Then delete secrets manually (CDK does not manage secret deletion by default):
```bash
aws secretsmanager delete-secret --secret-id "tech-news-agent/news-api" --recovery-window-in-days 7
aws secretsmanager delete-secret --secret-id "tech-news-agent/linkedin" --recovery-window-in-days 7
aws secretsmanager delete-secret --secret-id "tech-news-agent/instagram" --recovery-window-in-days 7
aws secretsmanager delete-secret --secret-id "tech-news-agent/youtube" --recovery-window-in-days 7
```

---

## Q: Why use us-east-1 as the default region?

It's the default in `AgentConfig.aws_region` because:
- AWS AgentCore and Bedrock models are available in `us-east-1`.
- New AWS services often launch in `us-east-1` first.

Override with `export AWS_REGION=eu-west-1` if you prefer a different region.
Ensure your chosen Bedrock model is available in that region.
