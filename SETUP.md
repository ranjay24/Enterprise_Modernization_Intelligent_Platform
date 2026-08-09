# EMIP — Setup

Quick start for local development and deploying to AWS. The canonical
deployment path is **AWS SAM** (`infrastructure/template.yaml`); the CDK stack
in `infrastructure/app.py` is experimental/legacy and should not be used.

## Prerequisites

- Python 3.14 (matches the Lambda runtime)
- Node.js 18+ / npm 9+
- AWS CLI v2 + SAM CLI v1 (`aws configure`)
- A working `.env` — start from `backend/.env.example`

## Local development

```powershell
# Backend (FastAPI)
cd backend
Copy-Item .env.example .env   # then edit to taste
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# Frontend (Vite, separate terminal)
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

The frontend proxies to the backend; see `frontend/src/services/jobService.ts`
for `API_BASE_URL`.

## Deploying with SAM

```powershell
cd infrastructure

# Validate + build (see package.json scripts: npm run validate / npm run build:backend)
sam validate --template template.yaml
sam build --template template.yaml

# Deploy to dev  (samconfig `default` section; stack emip-backend, -dev resources)
sam deploy --config-env default

# Deploy to staging  (samconfig `staging` section; stack emip-staging,
# resources named emip-*-staging, tables emip-jobs-staging/emip-analysis-staging)
sam deploy --config-env staging
```

Environment parameter files live in `infrastructure/parameters/`
(`dev.json`, `staging.json`). The Lambda layer must be Linux-built — see
`docs/14_DEPLOYMENT.md` → "Lambda Layer" and `layers/requirements.txt`.

## Environments

| Env | Stack | Tables | Bucket | API |
|-----|-------|--------|--------|-----|
| dev | emip-backend | emip-jobs-dev / emip-analysis-dev | emip-artifacts-dev-<acct> | …/dev |
| staging | emip-staging | emip-jobs-staging / emip-analysis-staging | emip-artifacts-staging-<acct> | …/staging |

Deployed Lambda environment variables come from the SAM template (Globals),
not from `.env`. The `.env` file is only used by a locally-running backend
that talks to deployed AWS resources.

## Frontend production build

```powershell
cd frontend
npm run build        # output in frontend/dist/
aws s3 sync dist/ s3://emip-frontend-<env>/
```

See `docs/14_DEPLOYMENT.md` for the full guide.
