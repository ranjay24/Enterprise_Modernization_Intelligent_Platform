# 18 — AWS Deployment & Cost Plan (Monolith → Microservices)

> Purpose: explain **how** the legacy monolith gets converted into microservices, **which AWS services** host it, and **what it costs** — both for the current `training-certificate-monolith` and as a **reusable model** for any future application uploaded to EMIP.
>
> All dollar figures are **estimates in US East (N. Virginia), on-demand, June 2026 list pricing** from AWS pricing pages. Your real bill depends on region, instance class, usage volume and AWS promotions — always confirm with the [AWS Pricing Calculator](https://calculator.aws) and your actual Cost Explorer data.

---

## 1. Current Application Snapshot (from EMIP analysis)

The uploaded ZIP is a **single-file Spring Boot monolith** (`TrainingCertificateMonolith.java`, 982 lines + a 14-line application class). EMIP's static analysis found:

| Metric | Value |
|---|---|
| Classes | 39 (all in one file, package `com.enterprise.training`) |
| Methods | 196 |
| Lines of code | ~744 |
| API endpoints | 6 (User, Course, Enrollment, Certificate controllers) |
| Database tables | 10 (users, courses, course_modules, enrollments, certificates, assessments, course_payments, notifications, student_profiles, compliance_audit_logs) |
| God class | `EnrollmentManagementService` (7 injected dependencies) |
| Long methods | `UserService.registerUser` (33 LOC), `EnrollmentManagementService.processEnrollmentAndIssuance` (46 LOC) |
| Dead code | `BaseEntity`, `LegacyPaperCertificatePrinter`, `OldGradeCalculator` |
| AI boundaries | 1 service, 37 classes, confidence 88, readiness green |

The god class `EnrollmentManagementService` orchestrates User, Course, Payment, Certificate, Notification, Assessment and Compliance — this is **the coupling that must be broken first** during conversion.

---

## 2. Target Architecture

Recommended decomposition into **7 microservices** (one per business domain):

```
                        ┌──────────────┐
 Client / Browser ─────▶│ CloudFront    │  CDN + TLS + WAF
                        └──────┬───────┘
                               ▼
                        ┌──────────────┐
                        │ API Gateway   │  HTTP API ($1/M calls) — auth, routing
                        └──────┬───────┘
                 ┌──────────────┼───────────────┬───────────────┐
                 ▼              ▼               ▼               ▼
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │ user-service│ │course-cat-  │ │enrollment-  │ │certificate- │
        │             │ │alog-service │ │service      │ │service      │
        └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                 │             │               │               │
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │assessment-  │ │notification-│ │compliance-  │ │(shared)     │
        │service      │ │service      │ │service      │ │auth/scheduler│
        └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘

   ECS Fargate (each service = 1 task, scaled independently)  ──▶ ALB in front
        │                                                    ──▶ ECR (images)
        ▼
   Data layer per service:
   ┌───────────────────────┬────────────────────────────────────┐
   │ RDS PostgreSQL (1-2 DBs)│ DynamoDB (audit/notification log)│
   │ relational/transactional│ high-volume/event data           │
   └───────────────────────┴────────────────────────────────────┘
        ▼
   Event bus:  SQS (queues) ─ SNS (topics) ─ EventBridge (rules)   (decouples
   enrollment → certificate → notification instead of direct calls)
```

**Service → source classes mapping (from EMIP analysis):**

| Microservice | Classes extracted | Owns data |
|---|---|---|
| **user-service** | User, UserController, UserRepository, UserService, StudentProfile, ApiResponse, GlobalExceptionHandler, DuplicateValidationUtils | users, student_profiles |
| **course-catalog-service** | Course, CourseModule, CourseRepository, CourseModuleRepository, CourseCatalogService, CourseController | courses, course_modules |
| **enrollment-service** | Enrollment, EnrollmentController, EnrollmentRepository, **EnrollmentManagementService** (split orchestration into an EventBus-driven flow), CourseFeePaymentService, CoursePayment, CoursePaymentRepository | enrollments, course_payments |
| **certificate-service** | Certificate, CertificateController, CertificateRepository, CertificateService (+ drop dead LegacyPaperCertificatePrinter / OldGradeCalculator) | certificates |
| **assessment-service** | Assessment, AssessmentRepository, AssessmentService | assessments |
| **notification-service** | Notification, NotificationRepository, NotificationService | notifications |
| **compliance-service** | ComplianceAuditLog, ComplianceAuditRepository, ComplianceAuditService | compliance_audit_logs |

**Key conversion decisions**
1. **Break the god class**: `EnrollmentManagementService.processEnrollmentAndIssuance` becomes an async saga over SQS/EventBridge (enroll → pay → issue certificate → notify) instead of 7 direct bean calls.
2. **Database-per-service** (loosely coupled): each service owns its tables in a private schema/DB; cross-service reads go through the API or events, never shared DAOs.
3. **API-first**: every service exposes a small REST API; the front-end talks only to API Gateway.
4. **Remove dead code** (BaseEntity, LegacyPaperCertificatePrinter, OldGradeCalculator) before conversion.
5. **Containers**: each service ships as a Docker image; the Spring context per service is tiny (split the mega-file into `src/main/java/<service>/…` packages).

---

## 3. Code Conversion Plan (phased)

### Phase 0 — Preparation (Week 0, ~$0 AWS)
- Re-run EMIP analysis on the monolith; freeze the extracted service boundaries as the target.
- Delete dead code; split the single file into normal package structure under a new Maven multi-module project.
- Set up Git repo, branch policy, and a **cost-tagging standard** (`env`, `service`, `team`).

### Phase 1 — Module refactor (Weeks 1–2)
- Split `TrainingCertificateMonolith.java` into 7 Maven modules with clear package boundaries.
- Introduce constructor injection for the split modules; keep behavior identical (refactor, no feature change).
- Write contract tests so migration is verifiable.

### Phase 2 — Strangler-fig extraction (Weeks 3–6)
- Extract services one at a time, lowest-risk first: **compliance** → **notification** → **assessment** (leaf services), then **certificate**, **course-catalog**, **user**, finally **enrollment** (the orchestrator).
- Each extraction: new module → Docker image → deploy to ECS Fargate → route a subset of traffic → compare contract tests → remove code from monolith.
- DB split per service (migration scripts + backfill + dual-write during transition).

### Phase 3 — Async decoupling (Weeks 7–9)
- Introduce SQS queues + EventBridge rules for the enrollment saga (pay → issue → notify).
- Idempotency keys + dead-letter queues per consumer.
- Replace direct bean-to-bean calls with events; keep REST fallbacks.

### Phase 4 — Cloud hardening (Weeks 10–11)
- API Gateway + ALB routing; WAF rules; Secrets Manager for DB credentials; IAM least-privilege.
- Auto-scaling per service (CPU/requests), health checks, multi-AZ for prod.
- Observability: CloudWatch dashboards + alarms, X-Ray traces, structured logs.

### Phase 5 — CI/CD & IaC (Weeks 12–13)
- CodePipeline/CodeBuild (or GitHub Actions) → ECR → ECS rolling deploy per service.
- CloudFormation/Terraform templates; one stack per environment (`dev`, `staging`, `prod`).
- Cost guardrails: budgets, alerts, auto-stop dev at night.

### Phase 6 — Acceptance (Week 14)
- Load test, failover test, cost review, runbook handover.

> **Engineering effort estimate** (2–3 developers): ~14–20 person-weeks total.
> At $50–80/hr (nearshore) → ~$28k–64k; at $100–150/hr (onshore) → ~$56k–120k.
> This is a **one-time build cost**; the AWS run-rate below is the recurring cost.

---

## 4. AWS Services to Use (and why)

| AWS Service | Role for the converted app | Notes |
|---|---|---|
| **ECS Fargate** | Runs every microservice as a container task | **Recommended over EKS**: no control-plane fee, simplest ops for <15 services |
| **EKS** (alternative) | Kubernetes orchestration | +$73/mo per cluster control plane; worth it only for large/heavy-K8s teams |
| **ECR** | Stores Docker images | ~$0.10/GB-month storage; free per-image data transfer to ECS in same region |
| **ALB** (Application Load Balancer) | Routes traffic to ECS services, TLS termination | $0.0225/hr + $0.008/LCU-hr |
| **API Gateway (HTTP API)** | Public REST API for the app | $1.00/M requests (REST v1 = $3.50/M — use HTTP) |
| **CloudFront** | CDN for front-end + API, cheaper egress | ~$0.085/GB egress |
| **Route 53** | Domain/DNS | $0.50/hosted zone/mo |
| **ACM** | Free TLS certificates | $0 |
| **WAF** | Web application firewall (DDoS/OWASP rules) | $5/mo per ACL + per-request |
| **RDS PostgreSQL** | Relational data (users, courses, enrollments, …) | Micro/Small instances first, Multi-AZ for prod |
| **DynamoDB** | Audit logs, notifications, event store | On-demand or provisioned; free tier 25GB |
| **S3** | File/artifact storage, log archive, static front-end | $0.023/GB-month |
| **SQS** | Async message queues (enrollment saga) | $0.40/M requests, 1M free/mo |
| **SNS** | Fan-out notifications (email/SMS/HTTP) | $0.50/M messages, 1M free/mo |
| **EventBridge** | Event routing between services | ~$1.00/M custom events |
| **Secrets Manager** | DB credentials, API keys | $0.40/secret/mo |
| **CloudWatch** | Logs, metrics, alarms | $0.50/GB logs ingested (5GB free), $0.30/metric, $0.10/alarm |
| **X-Ray** | Distributed tracing | ~$5 for first 100k traces/mo |
| **NAT Gateway** | Outbound internet for private-subnet tasks | $0.045/hr ($32.85/mo) **per AZ** + $0.045/GB |
| **VPC Endpoints** | Private access to S3/DynamoDB/ECR/CloudWatch (avoids NAT traffic) | ~$0.01/hr per endpoint/AZ + $0.01/GB |
| **Cognito** (optional) | User login/JWT | First 50k MAU free |
| **CodePipeline/CodeBuild** | CI/CD | CodeBuild ~$0.005/build-min; 100 free min/mo |
| **ECS Service Connect / Cloud Map** | Internal service discovery | Included/very low cost |
| **AWS Budgets / Cost Explorer** | Cost tracking & alerts | Free |

---

## 5. Unit-Price Reference (us-east-1, on-demand — used in every estimate below)

| Service | Unit | Price |
|---|---|---|
| Fargate vCPU | vCPU-hour | $0.04048 |
| Fargate memory | GB-hour | $0.004445 |
| Fargate ephemeral storage (>20GB) | GB-hour | $0.000111 |
| Fargate Spot (dev/staging) | — | ~68% cheaper |
| EKS control plane | cluster-hour | $0.10 (~$73/mo); +$0.50/hr if K8s version goes out of standard support |
| ALB | per hour | $0.0225 (~$16.40/mo) + $0.008/LCU-hr |
| NAT Gateway | per hour | $0.045 (~$32.85/mo) + $0.045/GB processed |
| API Gateway **HTTP** | per 1M requests | $1.00 (REST = $3.50) |
| API Gateway data transfer out | per GB | $0.09 |
| RDS db.t4g.micro | per month | ~$11.68 (single-AZ); ~$23.36 (Multi-AZ) |
| RDS db.t4g.small | per month | ~$23.36 (single-AZ); ~$46.72 (Multi-AZ) |
| RDS storage gp3 | per GB-month | ~$0.115 |
| DynamoDB on-demand writes | per 1M WRU | $1.25 *(AWS lists ~$0.63–1.25 by region/class)* |
| DynamoDB on-demand reads | per 1M RRU | $0.25 *(~$0.13–0.25)* |
| DynamoDB storage | per GB-month | $0.25 (25GB free) |
| S3 Standard | per GB-month | $0.023 |
| SQS | per 1M requests | $0.40 (1M free/mo) |
| SNS | per 1M messages | $0.50 (1M free/mo) |
| EventBridge custom events | per 1M | $1.00 |
| CloudWatch logs ingested | per GB | $0.50 (5GB free/mo) |
| CloudWatch log storage | per GB-month | $0.03 |
| CloudWatch custom metrics | per metric-mo | $0.30 (10 free) |
| CloudWatch alarms | per alarm-mo | $0.10 (10 free) |
| CloudFront egress | per GB | ~$0.085 (first 10TB) |
| Route 53 hosted zone | per month | $0.50 |
| WAF | per month | $5.00/ACL + ~$1.00/1M requests |
| Secrets Manager | per secret-month | $0.40 + $0.05/10k API calls |
| ECR storage | per GB-month | $0.10 |
| EC2 t3.micro (EKS/EC2 nodes) | per month | ~$7.60 |
| EC2 t3.small | per month | ~$15.20 |
| Data transfer out to internet | per GB | $0.09 (first 10TB) |

---

## 6. Cost Estimate for `training-certificate-monolith`

Assumptions: **ECS Fargate**, 7 services; dev runs business-hours (12h/day ≈ 264 h/mo), staging & prod 24/7; traffic ≈ 2M API calls/mo, ~10GB egress/mo, ~10GB logs/mo at prod.

### 6.1 Development (single AZ, no HA, can use Spot)

| Item | Basis | Monthly |
|---|---|---|
| Fargate (7 × 0.25 vCPU / 0.5 GB, 264 h) | 7×0.01234×264 | $22.80 |
| RDS db.t4g.micro (single-AZ) + 20GB gp3 | | $13.98 |
| NAT Gateway (1 AZ) | $32.85 | $32.85 *(optional)* |
| ECR (3GB) + S3 (2GB) + misc | | $2.00 |
| CloudWatch (≤5GB logs → free tier) | | $0.00 |
| **Dev total** | | **~$45 – $72** |

> Without NAT (dev-only: tasks on public subnets or VPC endpoints) → **~$39–45/mo**. Auto-stop at night or Fargate Spot → **~$25–35/mo**.

### 6.2 Staging (single AZ, mirrors prod topology)

| Item | Basis | Monthly |
|---|---|---|
| Fargate (7 × 0.5 vCPU / 1 GB, 24/7) | 7×0.024685×730 | $126.10 |
| RDS db.t4g.small (single-AZ) + 30GB gp3 | | $26.81 |
| ALB (base + 2 LCU avg) | 16.43 + 0.008×2×730 | $28.10 |
| NAT Gateway (1 AZ) | | $32.85 |
| CloudWatch (~6GB logs) | 1×0.50 | $0.50 |
| API Gateway (light) + ECR + S3 + messaging | | ~$5.00 |
| **Staging total** | | **~$220** *(with Fargate Spot → ~$134)* |

### 6.3 Production (HA, 2 AZ, 2 replicas per service)

| Item | Basis | Monthly |
|---|---|---|
| Fargate (14 tasks × 0.5 vCPU / 1 GB, 24/7) | 14×0.024685×730 | $252.30 |
| RDS db.t4g.small **Multi-AZ** + 30GB gp3 + backups | | $50.17 |
| ALB (base + LCUs) | 16.43 + ~8 | $24.40 |
| NAT Gateway (2 AZ) | 2×32.85 | $65.70 |
| API Gateway HTTP (2M req) + egress | 2×1.00 + ~0.9GB×0.09 | $2.08 |
| CloudWatch (logs 10GB, metrics, 8 alarms) | 5×0.50 + ~2 + 8×0.10 | $5.30 |
| CloudFront + Route 53 + WAF | 4 + 1 + 7 | $12.00 |
| DynamoDB (audit/notif, low volume) + S3 | | ~$5.00 |
| SQS + SNS + EventBridge (saga events) | | ~$3.00 |
| Secrets Manager (4 secrets) + ECR | | ~$2.60 |
| **Prod total** | | **~$423** |

### 6.4 Monthly summary

| Environment | Low (optimized) | High (on-demand, HA) |
|---|---|---|
| Dev | ~$35 | ~$72 |
| Staging | ~$134 (Spot) | ~$220 |
| Prod | ~$380 (Savings Plan) | ~$423 |
| **All three combined** | **~$550** | **~$715** |

**Annual run-rate: roughly $6,500 – $8,600/year** for this application fully hosted on AWS.

> **One-time engineering cost** (from §3): **$28k – $120k** depending on team location/rates. AWS infra is the *small* part of the total budget; engineering dominates.

---

## 7. ECS vs EKS — Decision for THIS app

| | ECS Fargate | EKS + Fargate | EKS + EC2 nodes |
|---|---|---|---|
| Control-plane fee | **$0** | +$73/mo | +$73/mo |
| Compute (14 tasks, prod) | $252 | $252 | ~$46 (3× t3.small) + ~$6 EBS |
| Ops effort | Lowest | Medium | Highest (node patches, scaling, K8s upgrades) |
| Prod monthly (added to other $170) | **~$423** | ~$496 | ~$295 |
| When to choose | **<15 services, small team → default** | K8s expertise already in team | High sustained utilization, autoscaling at scale |

**Recommendation: ECS Fargate.** EKS's $73/mo/cluster control-plane fee (and a $438/mo penalty if you forget to upgrade Kubernetes versions) rarely pays off below ~15–20 services. If you later need Kubernetes portability, migrate to EKS then — the Docker images are the same.

---

## 8. Cost Model for ANY Future Application (reusable)

To estimate any app EMIP will analyze, fill in **5 inputs** and use the formulas:

**Inputs**
1. `N` = number of microservices (≈ number of business domains EMIP detects; for this monolith it was 7)
2. `R` = monthly API requests (hits)
3. `D` = data volume (GB), and `logs_GB` = monthly log volume
4. `AZs` = availability zones in prod (1 dev, 1 staging, 2 prod)
5. `replicas` = instances per service (1 dev/staging, 2 prod for HA)

**Formulas (per month, US-East on-demand)**

```
Compute   = N × replicas × (0.25×0.04048 + 0.5×0.004445) × hours   // 0.25vCPU/0.5GB per service, hours=730 (or 264 dev)
Database  = RDS_instance_monthly (Micro 11.68 / Small 23.36) × AZ_multiplier(1 or 2) + D×0.115
Load bal  = 16.40 + 0.008 × LCUs            (LCUs ≈ R/1e6 × ~1.5)
NAT       = 32.85 × AZs + egress_GB × 0.045
API GW    = R/1e6 × 1.00  (HTTP)  +  egress_GB × 0.09
DynamoDB  = writes_M × 1.25 + reads_M × 0.25 + storage_GB × 0.25
Messaging = SQS_M×0.40 + SNS_M×0.50 + EBR_M×1.00
CloudWatch= max(0, logs_GB−5)×0.50 + custom_metrics×0.30 + alarms×0.10
Other     = S3(GB×0.023) + ECR + Secrets + Route53 + WAF(5) [+ CloudFront if web]
```

**Ready-made tiers** (assume 1 dev + 1 staging + 1 prod, on-demand, 2-AZ prod):

| Tier | N svcs | R (req/mo) | Data | Logs | **Est. monthly (all 3 envs)** |
|---|---|---|---|---|---|
| **S — Pilot/study** | 3 | 100K | 5 GB | 2 GB | **~$140 – $180** |
| **M — Small prod** (this app) | 7–8 | 2–5M | 50 GB | 10 GB | **~$550 – $720** |
| **L — Medium** | 15 | 50M | 500 GB | 100 GB | **~$1,400 – $1,800** |
| **XL — Large** | 30 | 500M | 5 TB | 1 TB | **~$5,500 – $7,000** |

**Rule-of-thumb**: every 10 microservices add ≈ $300–400/mo compute+overhead; every 1M API calls add ≈ $2–4; every 10 GB logs add ≈ $5; every extra AZ adds ≈ $33 (NAT) + DB 2×.

---

## 9. Cost Optimization Checklist

1. **ECS over EKS** for <15 services (saves $73/mo per cluster).
2. **Fargate Spot for dev/staging** (~68% cheaper; only use Spot-tolerant workloads).
3. **Schedule dev off-hours** (auto-stop nights/weekends) → cuts dev compute ~60%.
4. **Right-size tasks**: start 0.25–0.5 vCPU; scale only on measured CPU > 50%.
5. **HTTP API (not REST)** for API Gateway → $1.00 vs $3.50/M.
6. **VPC Endpoints for S3/DynamoDB/ECR/CloudWatch** instead of routing through NAT → avoids $0.045/GB NAT processing; can remove a NAT AZ in dev.
7. **Log retention 7–30 days**; ship cold logs to S3 (saves $0.50/GB/mo ingest).
8. **Reserved/Savings Plan** for 24/7 prod compute (up to 50% off Fargate).
9. **Use the AWS Free Tier** for the first 12 months (RDS micro, 1M API calls, 5GB logs, 25GB DynamoDB, 1M SQS/SNS).
10. **Budgets + cost tags**: tag every resource `env/service`, set AWS Budget alerts at 80/100%.

---

## 10. Tools to Monitor Cost

- **AWS Pricing Calculator** (calculator.aws) — build your exact stack.
- **Cost Explorer** — daily/monthly spend by service and tag.
- **AWS Budgets** — hard $ alerts (email/SNS).
- **EMIP integration**: EMIP's `ai_cost` stage already estimates per-service migration cost from the pipeline output — treat it as the *build* cost; use §8 for the *run* cost.

---

## 11. Assumptions & Disclaimer

- Prices = us-east-1 on-demand list (June 2026). Other regions (e.g., Mumbai, Singapore) are typically 5–20% higher.
- "High" totals assume no Savings Plans and 2-AZ HA prod; "Low" assumes Spot/scheduling and VPC-endpoint-optimized networking.
- Traffic beyond 10 TB/mo egress gets cheaper per GB ($0.085). Beyond 1M SQS/SNS the rates apply.
- DynamoDB on-demand figures are ranges; for predictable load, provisioned+reserved is ~30–70% cheaper.
- This document is a planning aid, **not a quote**. Confirm with AWS Pricing Calculator before committing.
