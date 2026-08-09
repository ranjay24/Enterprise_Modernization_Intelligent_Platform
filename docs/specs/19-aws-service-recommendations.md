# AWS Service Recommendations — End-to-End Feature (Spec 19)

## Problem

The product story is "upload ZIP → analyze → get microservices + the AWS services each one
should use". Today the **data contracts exist but are not wired into the running system**:

- `AIMigrationService.aws_services` (`backend/app/ai/contracts/migration.py:46`) and
  `AWSServiceRecommendation` (`backend/app/ai/contracts/developer.py:130`) define the shapes,
  but **no pipeline stage populates them**. The pipeline's `ai_migration` stage
  (`backend/app/pipeline/stages/ai_migration.py:35`) calls `generate_migration_waves()`
  (`backend/app/ai/orchestrator.py:1048`), which emits waves with a flat `services: [names]`
  list and **no AWS service data**.
- The frontend `MigrationWave` type (`frontend/src/types/api.ts:72`) has no `aws_services` field,
  so even if the backend sent it, nothing would render it.

Result: the "which AWS services will we use" deliverable that defines this product is **not shown
anywhere in the UI**.

## Goal

Make the AWS service target visible, end to end, with **real data** (not demo-only):

1. **Backend enabler (small)**: `generate_migration_waves()` deterministically attaches AWS
   service recommendations to each service, derived from real analysis signals. Offline-safe,
   no Bedrock, honest (follows the existing `sprint3-deterministic` generator pattern).
2. **Frontend**: render per-service AWS targets in two places — the **Migration Planner** wave
   drawer and a new **"AWS Target Architecture" section on the Results page**.
3. **Cleanup**: set up ESLint (#48) and replace the `dangerouslySetInnerHTML` in AIChat (#47).

## Data flow (target)

```
ai_migration stage
   └─ generate_migration_waves() ──► wave = { ...existing, 
          aws_services_map:      { "PaymentService": ["Amazon API Gateway", "AWS Lambda", ...] },
          aws_recommendations:   { "PaymentService": [ {service_name, use_case, justification,
                                                         alternatives, pricing_model,
                                                         free_tier_eligible} ] } }
        └─► analysis artifact ──► GET /api/results/{id}/analysis ──► frontend
   (services[] stays a plain string[] — codegen orchestrator + validator depend on that shape)
```

---

## Phase 1 — Backend enabler (deterministic AWS mapping)

**File to modify:** `backend/app/ai/orchestrator.py`

Add a module-level helper and attach its output in `generate_migration_waves()`. **Do not change**
the existing wave keys (`wave_number`, `name`, `services`, `timeline_weeks`, …) — the
codegen orchestrator (`backend/app/codegen/orchestrator.py:104`) and validator
(`backend/app/validation/analysis_validator.py:98`) read them.

### Mapping helper

```python
def recommend_aws_services(service: dict) -> list[dict]:
    """Deterministic AWS target recommendation for one boundary service.

    Returns AWSServiceRecommendation-shaped dicts:
    {service_name, use_case, justification, alternatives, pricing_model, free_tier_eligible}
    """
```

Rules (in priority order; all deterministic, no AI):

| Signal on service | AWS service | use_case | justification (template) |
|---|---|---|---|
| `api_endpoints` non-empty | `Amazon API Gateway` | "REST API exposure" | "Exposes N REST endpoints" |
| `database_tables` non-empty and any name matches `(mysql|oracle|postgres|sqlserver|db2|sql|schema|account|order|invoice|payment|customer)` | `Amazon RDS` | "Relational data store" | "Owns N relational tables" |
| `database_tables` non-empty otherwise | `Amazon DynamoDB` | "NoSQL data store" | "Owns N tables with no relational schema" |
| `broker_role` in `("kafka","both")` | `Amazon MSK` | "Event streaming" | "Publishes/subscribes inter-service events" |
| `broker_role` in `("rabbitmq","both")` | `Amazon MQ` | "Command queue" | "Uses RabbitMQ-style command queueing" |
| any class name in `(File|Blob|Attachment|Storage|Document|Upload|Download)` | `Amazon S3` | "Object/file storage" | "Handles file/blob artifacts" |
| always | `Amazon ECS on Fargate` **or** `AWS Lambda` | "Compute" | ">6 classes or DB-backed → Fargate; else Lambda" |
| always | `Amazon CloudWatch` | "Observability" | "Logs, metrics and alarms" |

Set `alternatives`, `pricing_model` ("pay-as-you-go") and `free_tier_eligible` (True) as sensible
constants. Cap recommendations at 6 per service.

### Wire into `generate_migration_waves()`

After a wave's `services` list is built (currently `backend/app/ai/orchestrator.py:1100-1148`),
attach two additive per-wave keys:

```python
waves.append({
    **existing_keys,                       # unchanged
    "aws_services_map": {                  # service_name -> short AWS names
        svc["name"]: [r["service_name"] for r in recommend_aws_services(svc)]
        for svc in group
    },
    "aws_recommendations": {               # service_name -> full recommendation dicts
        svc["name"]: recommend_aws_services(svc)
        for svc in group
    },
})
```

### Tests

New file `backend/tests/test_aws_service_recommendations.py`:

- REST-only service → `Amazon API Gateway` + compute, **no** DB service.
- Relational table name → `Amazon RDS`; non-relational table name → `Amazon DynamoDB`.
- `broker_role=kafka` → `Amazon MSK`; `rabbitmq` → `Amazon MQ`; `none` → neither.
- File class present → `Amazon S3`.
- `generate_migration_waves` output keeps `services` as `list[str]` **and** adds the two new keys.
- Empty `boundaries` still returns `{"waves": [], ...}` unchanged.
- Run: `cd backend && python -m pytest tests/test_aws_service_recommendations.py -v` then the full suite.

---

## Phase 2 — Frontend: types + two render locations

### Types (`frontend/src/types/api.ts`)

```ts
export interface AWSServiceRecommendation {
  service_name: string;
  use_case: string;
  justification: string;
  alternatives?: string[];
  pricing_model?: string;
  free_tier_eligible?: boolean;
}
```

Extend `MigrationWave` (keep existing fields; new ones **optional** so old saved results render fine):

```ts
aws_services_map?: Record<string, string[]>;
aws_recommendations?: Record<string, AWSServiceRecommendation[]>;
```

### Location A — Migration Planner wave drawer (`frontend/src/pages/MigrationPlannerPage.tsx`)

Insert a new "AWS Target Services" block **directly after the "Services" chips block**
(currently lines 219-226 of the wave detail side panel). For each service in
`selectedWave.services`, render:

```
Service name
  [Amazon API Gateway] [AWS Lambda] [Amazon DynamoDB]   ← chips from aws_services_map[svc]
```

- Use the existing chip style (`px-2 py-0.5 rounded bg-[var(--border-subtle)] text-[11px]`).
- If `aws_services_map` is missing/empty for a wave, render nothing (graceful, no placeholder).

### Location B — New "AWS Target Architecture" section on Results page

1. New component `frontend/src/components/results/AWSTargetSection.tsx`.
   Props: `waves: MigrationWave[]` and `services: ServiceBoundary[]`.
   - Flatten `aws_recommendations` across waves into a per-service grid.
   - Each service gets a card:
     - Header: service name + wave badge (`W1`, …).
     - Body: for each recommendation — `service_name` chip/icon, `use_case` (small label),
       `justification` (1-line secondary text), `pricing_model`/`free_tier_eligible` micro-badges.
   - Group services **by wave** (waves in order), each wave a titled subsection.
   - Empty state: if **no** wave has `aws_recommendations`, render nothing at all.
   - Follow the existing result-section visual conventions (see `components/results/` peers —
     card + `rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)]`).
2. Add it to `frontend/src/pages/ResultsPage.tsx` **immediately after**
   `<MicroserviceRecommendations recommendations={recommendations} />` (currently line 145) —
   i.e. services → their AWS target → then ADRs. Pass `waves={analysis.migration_waves}`.

### Demo / mock data (`frontend/src/data/mockResults.ts`)

Add `aws_services_map` + `aws_recommendations` to the existing `migration_waves` (starts line 265)
so demo mode previews the feature: e.g. `PaymentService` → API Gateway + ECS Fargate + RDS +
CloudWatch; `NotificationService` → API Gateway + Lambda + SNS + CloudWatch. Keep values
consistent with the existing demo services.

### Verification

- `cd frontend && npm run build` (typecheck + build) green.
- Manual: demo mode → Migration Planner → click a wave bar → drawer shows AWS chips.
  Results page → AWS Target Architecture section appears after microservice recommendations.

---

## Phase 3 — ESLint setup (#48)

Current state: `package.json` has a `lint` script (`eslint . --ext .tsx,.ts`, line 10) but
**eslint is not installed** and **no config exists**.

- Add devDependencies: `eslint@^8.57.0`, `@typescript-eslint/parser`, `@typescript-eslint/eslint-plugin`,
  `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`. (Use ESLint 8 + `.eslintrc.cjs` so the
  existing `lint` script keeps working; do not upgrade the CLI flags.)
- Add `frontend/.eslintrc.cjs` (parser `@typescript-eslint/parser`, plugins, extends
  `eslint:recommended` + `plugin:@typescript-eslint/recommended` + react-hooks recommended,
  ignore `dist`, `node_modules`, `vite.config.ts`).
- Run `npm run lint`; fix every violation (prefer `--fix` for auto-fixable, hand-fix the rest —
  do **not** add blanket `eslint-disable`).
- `npm run lint` must exit 0.

---

## Phase 4 — AIChat `dangerouslySetInnerHTML` removal (#47)

`frontend/src/components/chat/AIChat.tsx:254` renders assistant messages via
`dangerouslySetInnerHTML={sanitizeMarkdown(msg.content)}` (`sanitizeMarkdown` at line 22 builds an
HTML string). Remove both.

- Add `react-markdown` (new dependency; the demo answers include `## ` headings, code fences,
  and a markdown **table** — react-markdown handles all of them).
- Render assistant content as `<ReactMarkdown>{msg.content}</ReactMarkdown>` inside the existing
  bubble div. Delete `sanitizeMarkdown`. Keep the "Demo assistant · pre-written sample answers"
  banner text.
- `npm run build` green; verify the four suggested prompts still render (code block + table render
  correctly).

---

## Files to modify (complete list)

**Backend**
- `backend/app/ai/orchestrator.py` (modify) — `recommend_aws_services()` + wire into `generate_migration_waves()`
- `backend/tests/test_aws_service_recommendations.py` (new)

**Frontend**
- `frontend/src/types/api.ts` (modify) — `AWSServiceRecommendation` + 2 optional `MigrationWave` fields
- `frontend/src/pages/MigrationPlannerPage.tsx` (modify) — AWS chips block in wave drawer
- `frontend/src/components/results/AWSTargetSection.tsx` (new)
- `frontend/src/pages/ResultsPage.tsx` (modify) — mount AWSTargetSection after MicroserviceRecommendations
- `frontend/src/data/mockResults.ts` (modify) — demo `aws_services_map` + `aws_recommendations`
- `frontend/package.json` (modify) — eslint deps + `react-markdown`
- `frontend/.eslintrc.cjs` (new)
- `frontend/src/components/chat/AIChat.tsx` (modify) — react-markdown, remove innerHTML

**Docs / progress**
- `docs/specs/19-aws-service-recommendations.md` (this file)
- `docs/progress/in-progress.md` (start) / `docs/progress/completed.md` (finish)

## Rules to follow (EMIP repo)
1. Read this spec + `docs/17_AI_AGENT_GUIDE.md` before writing code.
2. Never modify artifact schemas (we are **adding keys**, not changing existing ones — no version bump).
3. Keep `services` as `list[str]` — codegen + validator depend on it.
4. No mock-only data without the demo banner context (demo data goes only in `mockResults.ts`).
5. Backend changes are additive and deterministic — no new Bedrock/AI calls.
6. Run: backend `python -m pytest tests/`, frontend `npm run lint` + `npm run build` before finishing.

## Acceptance Criteria
- [ ] `generate_migration_waves()` output includes `aws_services_map` + `aws_recommendations` per wave; `services` stays `string[]`.
- [ ] Backend suite green (465 baseline + new mapping tests).
- [ ] `MigrationWave` type carries the 2 new optional fields; old saved results render without error.
- [ ] Migration Planner wave drawer shows AWS service chips per service.
- [ ] Results page shows "AWS Target Architecture" section after microservice recommendations, grouped by wave, with use_case + justification + pricing model; empty when no data.
- [ ] Demo mode previews the feature via `mockResults.ts`.
- [ ] `npm run lint` passes (new eslint setup).
- [ ] AIChat renders via `react-markdown`; no `dangerouslySetInnerHTML` remains in the repo.
- [ ] `npm run build` green.

## Estimated Effort
- Phase 1: 0.5 day (backend helper + tests)
- Phase 2: 1.5-2 days (types + 2 render locations + demo data)
- Phase 3: 0.5 day
- Phase 4: 0.5 day
- **Total: ~3-4 days**

---

## Handover to Abhi

**Branch workflow (agreed):**
1. Lead pushes this spec to `main`. Abhi creates a feature branch off latest `main`:
   `git checkout main && git pull && git checkout -b feat/aws-service-recommendations`
2. Abhi implements against the branch, following the rules in §Files to modify.
3. Abhi runs the verification commands, then pushes his branch and opens a PR **to `main`** (no merge).
4. Lead reviews, then we integrate (resolve any overlap with our branch) and merge.

**Handover message for Abhi (WhatsApp/slack):**

> Abhi — new feature: AWS Service Recommendations (specs/19). Read
> docs/specs/19-aws-service-recommendations.md fully first. Branch off latest main:
> `git checkout -b feat/aws-service-recommendations`. It's 4 phases: (1) small backend
> deterministic mapping in ai/orchestrator.py + tests, (2) frontend types + two render
> locations (Migration Planner drawer + new Results "AWS Target Architecture" section),
> (3) ESLint setup, (4) AIChat innerHTML → react-markdown. All file paths + line anchors are in
> the spec. Must pass: `python -m pytest tests/`, `npm run lint`, `npm run build`. Push branch +
> open PR to main, don't merge yourself. Ping me when the PR is up.

### AI-agent prompt to paste into Abhi's coding agent

> You are implementing EMIP spec docs/specs/19-aws-service-recommendations.md in the repository
> at the repo root. Work ONLY on the files listed under "Files to modify (complete list)" in that
> spec, and follow every "Rules to follow" line in it.
>
> Implement all 4 phases exactly as specified:
> 1. Backend: add `recommend_aws_services(service: dict) -> list[dict]` in
>    backend/app/ai/orchestrator.py using the exact mapping table in the spec (API Gateway for
>    api_endpoints, RDS/DynamoDB for database_tables by name pattern, MSK/MQ for broker_role,
>    S3 for file classes, Fargate/Lambda for compute, CloudWatch always), and attach
>    `aws_services_map` + `aws_recommendations` per wave inside `generate_migration_waves()`
>    WITHOUT changing existing wave keys. Keep `services` as list[str]. Write
>    backend/tests/test_aws_service_recommendations.py covering the mapping rules + that services
>    stays string[] + empty-input behavior. Run `cd backend && python -m pytest
>    tests/test_aws_service_recommendations.py -v`, then the full suite, both must pass.
> 2. Frontend: add AWSServiceRecommendation to frontend/src/types/api.ts + the 2 optional
>    MigrationWave fields. Add the "AWS Target Services" chips block in the wave drawer of
>    MigrationPlannerPage.tsx (after the Services chips block). Create
>    frontend/src/components/results/AWSTargetSection.tsx and mount it in ResultsPage.tsx
>    immediately after <MicroserviceRecommendations>. Add realistic aws_services_map +
>    aws_recommendations to frontend/src/data/mockResults.ts migration_waves. Match the existing
>    card/chip visual conventions (--bg-card, --border-subtle tokens). Gracefully render nothing
>    when data is absent.
> 3. ESLint: add eslint@^8.57.0 + @typescript-eslint/* + react-hooks plugins to devDependencies,
>    create frontend/.eslintrc.cjs, fix all violations so `npm run lint` exits 0. Do not add
>    eslint-disable comments. Do not change the existing lint script.
> 4. AIChat: add react-markdown, render assistant messages with <ReactMarkdown>, delete
>    sanitizeMarkdown and the dangerouslySetInnerHTML usage. Verify the table + code-fence demo
>    answers render.
>
> Do NOT commit. Do NOT push. Do NOT create a PR. When done, report: every file changed,
> the exact test/lint/build results, and any deviation from the spec. Keep responses focused on
> the spec only.

---

## Notes for the lead

- Phase 1 is deliberately deterministic so the feature ships without depending on Bedrock and is
  unit-testable offline. A later sprint can swap in the AI `migration/migration_plan` prompt
  (which already models `aws_services`) and keep the same frontend contract.
- The two new wave keys are additive → no artifact schema version bump, no validator change, no
  codegen change.
- Our branch (frontend unit tests, dashboard real data, status alignment) touches
  `types/api.ts` and `mockResults.ts` too — plan a small merge together when integrating.
