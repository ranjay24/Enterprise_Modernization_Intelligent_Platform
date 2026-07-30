# EMIP — Enterprise Modernization Intelligence Platform

## Handover Guide — Sprint 5.5

---

### Table of Contents

1. [Project Overview](#1-project-overview)
2. [What's Completed vs Remaining](#2-whats-completed-vs-remaining)
3. [Backup & Safety — How to Revert](#3-backup--safety)
4. [AWS Account — Shared Access Setup](#4-aws-account--shared-access-setup)
5. [Prerequisites](#5-prerequisites)
6. [Local Development — Backend](#6-local-development--backend)
7. [Local Development — Frontend](#7-local-development--frontend)
8. [Deploy to AWS](#8-deploy-to-aws)
9. [Useful Commands](#9-useful-commands)
10. [Troubleshooting](#10-troubleshooting)

---

### 1. Project Overview

EMIP analyzes monolithic Java codebases (uploaded as ZIPs) and produces AI-driven recommendations for migrating to AWS microservices. It uses Amazon Bedrock (Nova Pro/Lite/Micro) for AI analysis.

**Tech Stack:**
- Backend: Python 3.14, FastAPI, Mangum (Lambda), Boto3
- Frontend: React 18, TypeScript, Vite 5, Tailwind CSS v3
- Infrastructure: AWS SAM + CDK (dual deployment)
- AI: Amazon Bedrock (Nova Pro, Nova Lite, Nova Micro)
- Database: DynamoDB, S3, SQS, SNS, EventBridge

---

### 2. What's Completed vs Remaining

| Area | Status | Notes |
|------|--------|-------|
| Backend API (5 routes: upload/analyze/results/jobs/deploy) | ✅ Complete | Tested, validated |
| 12-stage analysis pipeline | ✅ Complete | Sequential + parallel DAG support |
| Amazon Bedrock AI integration | ✅ Complete | Nova Pro/Lite/Micro with deterministic fallback |
| Static Java analyzer (regex-based) | ✅ Complete | Parses classes, endpoints, deps, god classes |
| Sprint 2 analysis engine (plugin-based) | ✅ Complete | 10 analyzer modules |
| Frontend (9 pages: Dashboard, Upload, Analysis, Results, Jobs, Reports, Architecture, Migration Planner, Settings) | ✅ Complete | Full demo mode with mock data |
| SAM + CDK infrastructure | ✅ Complete | S3, DynamoDB, SQS, SNS, EventBridge, Lambda |
| 249 tests passing | ✅ Complete | Sprint 3 + 5 integration + unit |
| Failure modes validated | ✅ Complete | 4-level graceful degradation |
| Sprint 5.5 validation (6 phases) | ✅ Complete | Environment, API, Pipeline, Failure Modes, Performance, Report |
| **Code generation in pipeline** | ⚠️ **Stubbed** | Pipeline writes `{}` for generated_code. `POST /deploy` calls Bedrock but pipeline doesn't wire it fully |
| **CI/CD (.github empty)** | ❌ **Not started** | All deployments are manual |
| **Frontend component tests** | ❌ **Not started** | Only backend tests exist |
| **CloudWatch dashboards & alarms** | ❌ **Not started** | No monitoring configured |
| **Docker compose / local dev env** | ❌ **Not started** | Dockerfile exists but no compose |
| **Knowledge base / docs** | ❌ **Empty** | `knowledge-base/` and `docs/` are empty |
| **Generated reports** | ❌ **Empty** | `reports/` directory is empty |

---

### 3. Backup & Safety

**Before handing over, run this to create a safety baseline:**

```bash
cd C:\Users\ADMIN\Desktop\ProjectOne
git init
git add .
git commit -m "Baseline Sprint 5.5 — validated and stable"
```

Now you have a tagged commit you can always return to.

**If you're sharing via zip:**
1. Run `git init && git add . && git commit -m "baseline"` first
2. Zip the folder (the `.git` history travels with it)
3. Exclude: `node_modules/`, `__pycache__/`, `.aws-sam/`, `cdk.out/`, `*.pyc`, `.env`

**To restore your baseline later:**
```bash
git checkout main   # or whatever branch you committed to
```

**If they use the same git repo:**
- Keep `main` as your branch
- Have them work in a branch like `team-dev`
- You can always diff or revert

---

### 4. AWS Account — Shared Access Setup

**Do NOT share your root/admin credentials.** Create an IAM user for the team.

1. Go to AWS Console → IAM → Users → Create user
2. Name: `emip-dev-team`
3. Attach the policy from `infrastructure/policies/iam-team-policy.json` (created below)
4. Enable programmatic access → Generate access key
5. Share only these credentials with your team

**Policy to attach** (create as `infrastructure/policies/iam-team-policy.json`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
        "s3:ListBucket", "s3:GetBucketLocation"
      ],
      "Resource": [
        "arn:aws:s3:::emip-artifacts-479752407378",
        "arn:aws:s3:::emip-artifacts-479752407378/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem",
        "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:479752407378:table/emip-jobs",
        "arn:aws:dynamodb:us-east-1:479752407378:table/emip-jobs/index/*",
        "arn:aws:dynamodb:us-east-1:479752407378:table/emip-analysis",
        "arn:aws:dynamodb:us-east-1:479752407378:table/emip-analysis/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage",
        "sqs:GetQueueAttributes", "sqs:GetQueueUrl"
      ],
      "Resource": [
        "arn:aws:sqs:us-east-1:479752407378:emip-analysis-queue-dev",
        "arn:aws:sqs:us-east-1:479752407378:emip-analysis-dlq-dev"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:us-east-1:479752407378:emip-notifications-dev"
    },
    {
      "Effect": "Allow",
      "Action": [
        "events:PutEvents"
      ],
      "Resource": "arn:aws:events:us-east-1:479752407378:event-bus/emip-events-dev"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup", "logs:CreateLogStream",
        "logs:PutLogEvents", "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

**Revoke access anytime** by deleting the IAM user or disabling their keys.

---

### 5. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.14 | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| AWS CLI | 2.x | `aws --version` |
| SAM CLI | 1.x | `sam --version` |
| AWS CDK | 2.x | `cdk --version` |

**AWS credentials must be configured:**
```bash
aws configure
# Enter the access key and secret from step 4
# Default region: us-east-1
```

---

### 6. Local Development — Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env with your values (see notes below)

# Run locally
uvicorn app.main:app --reload --port 8000
```

**Backend runs at:** http://localhost:8000
**API docs:** http://localhost:8000/docs
**Health check:** http://localhost:8000/health

**`.env` notes:**
- `AWS_REGION`, `AWS_ACCOUNT_ID` — already set for your account
- `S3_BUCKET` — the bucket name with your account ID suffix (e.g. `emip-artifacts-479752407378`)
- `DYNAMODB_JOBS_TABLE` — `emip-jobs`
- `DYNAMODB_ANALYSIS_TABLE` — `emip-analysis`
- `EMIP_API_KEY` — leave empty to disable API key auth locally
- `CORS_ORIGINS` — keep `["http://localhost:5173"]` for frontend dev

**Lambda layer (for local testing of worker):**
Not needed for local dev. The worker path is skipped when `AWS_LAMBDA_FUNCTION_NAME` is not set.

---

### 7. Local Development — Frontend

```bash
cd frontend
npm install
npm run dev
```

**Frontend runs at:** http://localhost:5173

The Vite dev server proxies `/api` and `/health` requests to `http://localhost:8000` (your backend).

---

### 8. Deploy to AWS

**Option A — SAM (recommended for simplicity):**
```bash
cd infrastructure
sam build
sam deploy --guided
# Follow prompts, use defaults from samconfig.toml
```

**Option B — CDK:**
```bash
cd infrastructure
npx cdk bootstrap
npx cdk deploy EMIP-Backend
```

**After deploy, update the frontend:**
1. Set `VITE_API_KEY` in `frontend/.env` if API key auth is enabled
2. The frontend proxies `/api` to the backend URL in dev mode
3. For production, build the frontend and serve it from S3/CloudFront or your preferred host

---

### 9. Useful Commands

```bash
# Reset all data (DynamoDB + S3 + checkpoints)
python scripts/fresh_start.py

# List DynamoDB jobs
aws dynamodb scan --table-name emip-jobs

# Purge SQS queue (re-queue messages)
aws sqs purge-queue --queue-url <queue-url>

# Check Lambda logs
aws logs tail /emip/backend --follow
aws logs tail /emip/worker --follow

# Frontend build
cd frontend && npm run build    # outputs to dist/

# CDK synth (generate CloudFormation without deploying)
cd infrastructure && npx cdk synth
```

---

### 10. Troubleshooting

| Problem | Solution |
|---------|----------|
| `NoCredentialsError` | Run `aws configure` or check `AWS_ACCESS_KEY_ID` env vars |
| `AccessDenied` on S3/DynamoDB | IAM user policy doesn't match resource ARNs. Check account ID in ARNs |
| Frontend can't reach backend | Ensure backend is running on :8000. Check `vite.config.ts` proxy settings |
| Pipeline fails silently | Check CloudWatch logs for the worker Lambda: `aws logs tail /emip/worker` |
| Bedrock "AccessDeniedException" | Ensure Bedrock model access is enabled in us-east-1 for Nova models |
| `ExpressionAttributeNames=None` | Fixed in Sprint 5.5 — ensure you're on the latest code |
| Empty ZIP rejected | Fixed in Sprint 5.5 — validator rejects 0-entry archives |

---

*Handover prepared 2026-07-30. Project validated at Sprint 5.5 with 249 passing tests.*
