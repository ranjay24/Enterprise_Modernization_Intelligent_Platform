# EMIP Deployment Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| AWS CLI | v2.x | AWS authentication and resource management |
| SAM CLI | v1.x | Serverless Application Model deployment |
| Python | 3.14+ | Lambda runtime (must match exactly) |
| Node.js | 18+ | Frontend build |
| npm | 9+ | Frontend dependency management |

Verify prerequisites:

```powershell
aws --version
sam --version
python --version
node --version
npm --version
```

Configure AWS CLI with appropriate credentials:

```powershell
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region: us-east-1
# Default output: json
```

## SAM Deployment (Primary)

EMIP uses AWS SAM (`infrastructure/template.yaml`) as the primary deployment mechanism.

### 1. Build the SAM Template

```powershell
cd infrastructure
sam build --template template.yaml
```

This processes the template, resolves local paths, and creates the build artifacts in `.aws-sam/`.

### 2. First-Time Deployment (Guided)

```powershell
sam deploy --guided
```

You will be prompted for:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Stack Name` | `emip-backend` | CloudFormation stack name |
| `AWS Region` | `us-east-1` | Deployment region |
| `Environment` | `dev` | Environment: `dev`, `staging`, or `prod` |
| `LogLevel` | `INFO` | Logging level |
| `ApiKey` | (empty) | API key for authentication |
| `DynamoDBJobsTable` | `emip-jobs-dev` | Jobs DynamoDB table name |
| `DynamoDBAnalysisTable` | `emip-analysis-dev` | Analysis DynamoDB table name |
| `Confirm changes before deploy` | `Yes` | Review changeset before deploying |
| `Allow SAM CLI IAM role creation` | `Yes` | Allow creation of IAM roles |
| `Save arguments to samconfig.toml` | `Yes` | Save configuration for future deploys |

### 3. Subsequent Deployments

```powershell
sam deploy
```

Uses the saved configuration from `samconfig.toml`. To use a different environment:

```powershell
sam deploy --config-env prod
```

### Environment-Specific Parameter Files

Parameter overrides can be specified via command line:

```powershell
# Dev deployment
sam deploy --parameter-overrides Environment=dev LogLevel=INFO

# Prod deployment
sam deploy --parameter-overrides Environment=prod LogLevel=WARNING ApiKey=<prod-key>
```

## CDK Deployment (Alternative)

AWS CDK (`infrastructure/app.py`) is available as an alternative deployment mechanism.

### 1. Bootstrap CDK

```powershell
cd infrastructure
cdk bootstrap aws://<account-id>/us-east-1
```

This creates the CDK toolkit stack in your account (required once per region).

### 2. Deploy the Stack

```powershell
cdk deploy EMIP-Backend
```

### 3. View Outputs

```powershell
cdk outputs
```

## Lambda Layer

The Lambda layer contains all Python dependencies. It is built separately and referenced by the SAM template.

### Build the Layer

```powershell
cd layers
pip download -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: -d dependencies/
cd dependencies
zip -r ../dependencies.zip .
```

The SAM template at `infrastructure/template.yaml` references the layer at `ContentUri: ../layers/dependencies/`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMIP_ENV` / `ENVIRONMENT` | `dev` | Deployment environment (`dev`, `staging`, `prod`) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `S3_BUCKET` | `emip-artifacts` | S3 bucket for analysis artifacts |
| `TABLE_PREFIX` / `DYNAMODB_JOBS_TABLE` | `emip-jobs-dev` | DynamoDB jobs table |
| `DYNAMODB_ANALYSIS_TABLE` | `emip-analysis-dev` | DynamoDB analysis table |
| `BEDROCK_MODEL_PRIMARY` | `amazon.nova-pro-v1:0` | Primary Bedrock model |
| `BEDROCK_MODEL_FALLBACK` | `amazon.nova-lite-v1:0` | Fallback Bedrock model |
| `BEDROCK_MODEL_CODEGEN` | `amazon.nova-pro-v1:0` | Code generation model |
| `QUEUE_PREFIX` / `SQS_ANALYSIS_QUEUE` | `emip-analysis-queue` | Analysis SQS queue |
| `SQS_ANALYSIS_DLQ` | `emip-analysis-dlq` | Analysis dead letter queue |
| `SNS_NOTIFICATION_TOPIC` | `emip-notifications` | Notification SNS topic |
| `EVENTBRIDGE_BUS_NAME` | `emip-events` | EventBridge bus |
| `ENABLE_XRAY` | `false` | Enable AWS X-Ray tracing |
| `API_KEY` | (empty) | API key for authentication |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `CHECKPOINT_ENABLED` | `true` | Enable pipeline checkpointing |
| `ARTIFACT_VERSION` | `1.0.0` | Artifact format version |

## Frontend Build

```powershell
cd frontend
npm install
npm run build
```

The build output is placed in `frontend/dist/`. Deploy the `dist/` folder to an S3 bucket configured for static website hosting or CloudFront:

```powershell
aws s3 sync dist/ s3://emip-frontend-<env>/
```

For CloudFront, invalidate the cache after deployment:

```powershell
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```

Frontend configuration is in `frontend/src/services/jobService.ts` — update the `API_BASE_URL` to point to the deployed API Gateway URL.

## Rollback

### SAM Rollback

If a deployment fails or introduces issues, roll back to a previous version:

```powershell
sam deploy --stack-name emip-backend --capabilities CAPABILITY_IAM
```

Or use CloudFormation console to roll back to a previous stack version:

```powershell
aws cloudformation rollback-stack --stack-name emip-backend
```

### List Stack Events

```powershell
aws cloudformation describe-stack-events --stack-name emip-backend
```

## Production Deployment

For production deployments:

1. **Use a separate parameter file** with production values:
   ```powershell
   sam deploy --parameter-overrides Environment=prod LogLevel=WARNING ApiKey=<strong-key>
   ```

2. **Increase Lambda configuration**:
   - Memory: 2048 MB (vs 1024 MB for dev)
   - Timeout: 300 seconds (vs 120 seconds for dev)
   - These are set in `infrastructure/template.yaml` under `Globals.Function`.

3. **Enable CloudWatch alarms** for:
   - Lambda error rate > 1%
   - SQS queue depth > 100
   - API Gateway 5xx rate > 1%
   - Bedrock invocation failures

4. **Enable X-Ray tracing**:
   ```powershell
   sam deploy --parameter-overrides Environment=prod EnableXRay=true
   ```

5. **Set up SNS notifications** for deployment events and alarm states.

6. **Use an API key** — set the `ApiKey` parameter and configure clients to send it via the `X-API-Key` header.

## CI/CD

**CI/CD is not yet configured** — manual deployment is required. CI/CD is planned for Sprint 6+.

For now, follow the manual deployment steps above. Consider automating with:

- GitHub Actions workflow in `.github/workflows/`
- AWS CodePipeline with CodeBuild
- SAM Pipelines (`sam pipeline init`)

## Troubleshooting

### Common Issues and Solutions

| Issue | Likely Cause | Solution |
|-------|-------------|----------|
| `sam build` fails | Missing Python dependencies | Ensure `requirements.txt` includes all packages; run `pip install -r requirements.txt` |
| `sam deploy --guided` timeout | IAM role creation pending | Pre-create IAM roles or use `--capabilities CAPABILITY_IAM` |
| Lambda runtime error: `Unable to import module` | Layer build incompatible with Lambda runtime | Rebuild layer targeting `python3.14` with `manylinux2014_x86_64` |
| API Gateway 503 | Lambda concurrency exceeded | Increase Lambda reserved concurrency; check for throttling |
| Bedrock access error | Model access not granted in AWS region | Request model access in AWS Bedrock console |
| Frontend CORS errors | API Gateway CORS config mismatch | Verify `CORS_ORIGINS` includes frontend origin |
| Artifact not found in S3 | Bucket prefix mismatch | Check `S3_BUCKET` and `jobs/{job_id}/artifacts/` path |
| Cold start latency | Lambda initialization overhead | Use Lambda SnapStart (Java) or provisioned concurrency |
| `samconfig.toml` not found | Wrong working directory | Ensure you are in the `infrastructure/` directory |

### Debugging Deployments

1. Check CloudFormation stack events:
   ```powershell
   aws cloudformation describe-stack-events --stack-name emip-backend
   ```

2. View Lambda logs in CloudWatch:
   ```powershell
   aws logs tail /aws/lambda/emip-backend-FastAPIFunction-<id>
   ```

3. Test API Gateway locally with SAM:
   ```powershell
   sam local start-api
   ```

4. Invoke Lambda function directly:
   ```powershell
   sam local invoke "FastAPIFunction" -e events/apigw-test.json
   ```
