# Cognito Authentication — Login, Signup, and Demo Mode

## Problem
The platform has no user concept: any caller with the API key can invoke every endpoint, and the
frontend has no login/signup flow. The external security review (Phase 9) flagged missing authN/authZ.

## Goal
Add opt-in **Amazon Cognito** authentication, end to end, without breaking the current
API-key-only deployments (all new resources are behind a `CreateCognitoPool` flag that defaults
to `false`).

Phase 1 (this spec): backend enforcement + `/api/auth/*` routes + SAM user pool + frontend auth
pages with a demo-mode bypass. Deploy is deferred until all phases are complete.

```
React (login/signup) ──► POST /api/auth/login ──► cognito-idp initiate_auth ──► IdToken/AccessToken
                                   │
   every subsequent request  ──►  Authorization: Bearer <IdToken>
                                   │
                            CognitoAuthMiddleware (JWKS) ──► 200 / 401
```

## Settings (backend/app/core/settings.py)
| Field | Env | Default | Notes |
|---|---|---|---|
| `cognito_enabled` | `EMIP_COGNITO_ENABLED` | `false` | Master switch; `false` = today's behavior |
| `cognito_user_pool_id` | `EMIP_COGNITO_USER_POOL_ID` | `""` | Required when enabled |
| `cognito_region` | `EMIP_COGNITO_REGION` | `us-east-1` | Region hosting the pool |
| `cognito_client_id` | `EMIP_COGNITO_CLIENT_ID` | `""` | App client id (no secret → `USER_PASSWORD_AUTH`) |

Bound via `AliasChoices("EMIP_*", "*", "<field>")` matching the existing `api_key` pattern.

## Backend
- `backend/app/core/security.py` — new `CognitoAuthMiddleware`:
  - When `cognito_enabled=false` → pass-through (zero behavior change).
  - Validate `Authorization: Bearer <IdToken>` against the pool JWKS (python-jose
    `PyJWKClient`), checking expiry, `aud == cognito_client_id`, and `iss ==
    https://cognito-idp.<region>.amazonaws.com/<pool_id>`.
  - Missing/invalid token → `401`. `/api/health` and `/api/auth/*` stay public.
  - API-key auth continues to work in parallel (either credential is accepted).
- `backend/app/routes/auth.py` (new router, no auth middleware):
  - `POST /api/auth/login` — `cognito-idp.initiate_auth` `USER_PASSWORD_AUTH` → `{id_token,
    access_token, refresh_token, expires_in, user}`; wrong password → 401; unconfirmed → 400
    with `confirm_required: true`; Cognito disabled → 503.
  - `POST /api/auth/signup` — self-service sign-up (`UserPoolClient` → `UserPool` create);
    duplicate → 409.
  - `POST /api/auth/confirm` — confirm the sign-up code.
  - `POST /api/auth/refresh` — exchange a refresh token for fresh tokens.
  - `GET /api/auth/me` — return the JWKS-validated identity from the bearer token.
- `backend/app/aws/clients.py` — lazy `cognito-idp` client.
- `backend/app/main.py` — mount the middleware + include the auth router.

## SAM (infrastructure/template.yaml)
- New `CreateCognitoPool` param (default `false`) + `CognitoDomainPrefix` (default `""`).
- Conditional `EmipUserPool`, `EmipUserPoolClient` (`GenerateSecret: false`,
  `ALLOW_USER_PASSWORD_AUTH` + `ALLOW_REFRESH_TOKEN_AUTH`), `EmipUserPoolDomain`.
- Env wiring `EMIP_COGNITO_*` into both Lambda functions; outputs `CognitoUserPoolId`,
  `CognitoClientId`, `CognitoHostedUIDomain`.
- Demo user (no admin-create IAM in the template): run
  `aws cognito-idp admin-create-user --user-pool-id <id> --username <email> --temporary-password DemoPass123! --message-action SUPPRESS`
  then `admin-set-user-password` once per environment. Documented in docs/06.

## Frontend (done)
- `frontend/src/auth/AuthContext.tsx` + `storage.ts` + `types.ts` — status machine, token persistence, guest/demo bypass.
- `frontend/src/pages/LoginPage.tsx` + `SignupPage.tsx` — rendered outside the app shell; unauthenticated users are gated to `/login`.
- Store the tokens; attach `Authorization: Bearer` on every API call (request interceptor); 401 → session cleared + redirect.
- **Demo mode**: when the backend reports 503 (Cognito disabled), the app uses a guest session + sample data (honest banner), preserving today's no-backend demo experience; the login page has an explicit "Continue in Demo Mode" button.
- Notification banner integrating with job status: `frontend/src/hooks/useNotifications.ts` + TopNav dropdown/toast (eye-catchy pulsing bell + slide-down toast).

## Files to modify (frontend)
- backend/app/core/settings.py (modify) — Cognito fields
- backend/app/core/security.py (modify) — CognitoAuthMiddleware
- backend/app/routes/auth.py (new)
- backend/app/aws/clients.py (modify) — cognito-idp client
- backend/app/main.py (modify) — middleware + router
- backend/tests/test_auth_cognito.py (new) — 19 tests
- infrastructure/template.yaml (modify) — conditional pool + env wiring
- backend/.env.example (modify) — Cognito block
- frontend/src/auth/AuthContext.tsx, storage.ts, types.ts (new)
- frontend/src/services/api.ts (modify) — bearer interceptor + 401 handling
- frontend/src/pages/LoginPage.tsx, SignupPage.tsx (new)
- frontend/src/App.tsx (modify) — AuthProvider, gate, /login /signup routes
- frontend/src/components/layout/TopNav.tsx, Sidebar.tsx, UserChip.tsx (modify/new)
- frontend/src/hooks/useNotifications.ts (new) — job-status notifications
- frontend/src/pages/SettingsPage.tsx (modify) — Account card
- frontend/tailwind.config.js (modify) — slide-down keyframe
- frontend/src/store/useAppStore.ts (modify) — setDemoMode
- tests/e2e/auth-gate.spec.ts (new) — 5 auth-gate e2e tests
- docs/progress/in-progress.md / completed.md (modify)
- docs/specs/18-cognito-auth.md (new)

## Acceptance Criteria
- [x] All Cognito SAM resources are behind `CreateCognitoPool=false` → existing stacks unchanged.
- [x] Bearer-token auth enforced only when `cognito_enabled=true`; API key still accepted.
- [x] Login / signup / confirm / refresh / me endpoints work and return honest 503 when disabled.
- [x] `GET /api/auth/me` returns 503 (not 401) when Cognito is disabled — the frontend probe signal.
- [x] Backend suite green (449 passed).
- [x] Login/signup pages render outside the app shell; gate redirects unauthenticated users to `/login`.
- [x] Tokens persisted and attached as `Authorization: Bearer` on every API call; 401 → session cleared.
- [x] Demo-mode bypass: demo flag → guest session (no login); 503/network probe → guest; login page has a "Continue in Demo Mode" button.
- [x] Real user identity (name/email) in Sidebar, TopNav, and Settings Account card — fabricated profile removed.
- [x] Job-status notification dropdown + toast (pulsing bell, unseen badge), demo-seeded in demo mode.
- [x] Playwright auth-gate e2e (5 tests) + existing demo walkthrough (13) → 18/18 passed.

## Estimated Effort
3-5 days total (backend 2 days, frontend 2-3 days).
