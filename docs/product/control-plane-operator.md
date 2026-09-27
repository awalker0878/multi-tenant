# Control API, portal and operator CLI

The first control-plane slice lets an authenticated sysadmin browse workload records in an exact workload security domain (WSD), record approvals, admit an already approved migration plan as a job, and read the persisted job timeline. The portal and `hosting-operator` CLI call the same HTTP API. An access scope in the portal is a verified role assignment; it is **not** a claim that an environment has been deployed or qualified.

## Deploy the service

Install the package with its `controlplane` extra. Apply the packaged PostgreSQL migrations with a separate migration owner before starting the API. Provision distinct non-superuser, non-`BYPASSRLS` PostgreSQL roles for the API runtime, the authority ledger writer, and the global read-only IAM directory resolver. Grant only the permissions in the [migration runbook](../../provisioner/controlplane/persistence/migrations/README.md). The API checks that the three roles are live and distinct before listening.

Provide the following settings through a secret manager or protected process environment. Never put database passwords or SSO tokens in command arguments, repository files, or URLs.

| Setting | Purpose |
| --- | --- |
| `HOSTING_RUNTIME_DSN` | Tenant records and jobs; TCP PostgreSQL DSN with `sslmode=verify-full` |
| `HOSTING_AUTHORITY_DSN` | Dedicated approval/revocation writer, also used for authoritative plan reads |
| `HOSTING_DIRECTORY_DSN` | Global read-only enrollment/session/grant resolver |
| `HOSTING_OIDC_ISSUER` | Pinned HTTPS OIDC issuer |
| `HOSTING_OIDC_AUDIENCE` | Exact control API access-token audience |
| `HOSTING_OIDC_JWKS_URI` | Pinned HTTPS JWKS endpoint |
| `HOSTING_STEP_UP_ACR` | Comma-separated verified ACR values allowed for approval and revocation |
| `HOSTING_LISTEN_HOST`, `HOSTING_LISTEN_PORT` | Loopback listener; defaults `127.0.0.1:8080` |

The human role directory is fed by signed, bounded IAM snapshots using a separately credentialed writer. A JWT alone never establishes tenant membership or a grant. The API queries current enrollment/session/grants on each request. The issuer must provide RS256 `at+jwt` access tokens with the required audience and claims as specified in the [OIDC verifier](../../provisioner/controlplane/authority/oidc.py).

Run `hosting-api` behind a dedicated HTTPS reverse proxy on the same host. The proxy must set the external `Host` and overwrite `X-Forwarded-Proto`; the service trusts forwarded headers only from loopback. Apply a matching ingress request-size limit. The service does not start if any required identity or database configuration is absent.

To enable the portal, additionally set the five required portal settings below. Its redirect URI is exactly `<HOSTING_PORTAL_ORIGIN>/portal/callback`; register that HTTPS URI as an OIDC public client using Authorization Code, PKCE S256 and `form_post`. With these settings absent, `/portal/` is unavailable.

| Setting | Purpose |
| --- | --- |
| `HOSTING_PORTAL_ORIGIN` | Dedicated exact HTTPS portal origin |
| `HOSTING_PORTAL_AUTHORIZE_URL` | Authorization endpoint on the pinned issuer origin |
| `HOSTING_PORTAL_TOKEN_URL` | Token endpoint on the pinned issuer origin |
| `HOSTING_PORTAL_CLIENT_ID` | Public OIDC client identifier |
| `HOSTING_PORTAL_SCOPE` | Scope containing `openid`, without `offline_access` |
| `HOSTING_PORTAL_STEP_UP_ACR` | Optional one ACR from `HOSTING_STEP_UP_ACR`; enables a fresh IdP reauthentication before portal approval |

The portal keeps its access token in the active page's memory, uses a self-hosted script/style bundle and a restrictive Content Security Policy, and does not store tokens in URLs, cookies or browser storage. Closing or reloading the page requires signing in again. An independently managed TLS proxy, IdP client registration and IAM sync are still required to use it.

## Operator flow

Obtain a short-lived control API access token through the organization's approved SSO method and pipe it to `hosting-operator --token-stdin`. The CLI refuses non-HTTPS API URLs except loopback for local integration tests. It validates TLS, does not follow redirects or use proxy settings from the environment, and does not print the token.

```text
<approved SSO tool producing one token line> | hosting-operator --api-url https://control.example.org --token-stdin scopes
<approved SSO tool producing one token line> | hosting-operator --api-url https://control.example.org --token-stdin workloads list --wsd wsd-01
<approved SSO tool producing one token line> | hosting-operator --api-url https://control.example.org --token-stdin plans review --id plan-01
<approved SSO tool producing one token line> | hosting-operator --api-url https://control.example.org --token-stdin jobs events --id job-01
```

Each CLI invocation reads one token line. The job submit command requires a stable `--idempotency-key` retained by the operator for retries. It cannot bypass four current plan approvals, separation of duties, exact source/destination scopes, or the transactional admission recheck. Its response is the persisted `QUEUED` job, not a claim that a native operation has begun.

An approver must first review the current plan through `plans review --id PLAN_ID`. The response contains the current revision and digest, source and destination scopes, route method, selected resource counts, and downtime/data-loss/rollback limits. It does not contain native mappings or the plan author. After checking those facts, obtain a freshly stepped-up SSO token and pass `--expected-revision` and `--expected-digest` with `approvals record`. If the plan changes before recording, the API returns `PLAN_REVIEW_STALE` and no approval is written. The portal applies the same binding when its optional step-up ACR is configured.

```text
<approved step-up SSO tool producing one token line> | hosting-operator --api-url https://control.example.org --token-stdin approvals record --plan plan-01 --role SOURCE_OWNER --ttl-seconds 300 --expected-revision 1 --expected-digest <64-character digest from review>
```

| HTTP operation | Behavior |
| --- | --- |
| `GET /v1/access/scopes` | Current verified WSD/site role selectors, not environment inventory |
| `GET /v1/wsds/{wsdId}/workloads` | SQL-filtered workload page within one authorized WSD |
| `GET /v1/wsds/{wsdId}/workloads/{workloadId}` | Workload within the same authorized WSD |
| `POST /v1/wsds/{wsdId}/workloads` | Create a canonical `PLANNED` workload without native-binding claims |
| `GET /v1/plans/{planId}/review` | Show redacted current plan facts to an exact scoped reviewer |
| `POST /v1/plans/{planId}/approvals` | Record one stepped-up owner/security approval only for the reviewed revision and digest |
| `POST /v1/plans/{planId}/revoke` | Advance the durable revocation epoch with a reason |
| `POST /v1/plans/{planId}/jobs` | Atomically admit an approved plan with `Idempotency-Key` |
| `GET /v1/jobs/{jobId}` | Read a tenant-scoped job if the actor has both persisted native-scope grants |
| `GET /v1/jobs/{jobId}/events` | Read recorded event type/status/sequence; unredacted details are withheld |

The API publishes `/openapi.json`; interactive CDN-backed API documentation is disabled. Approval receipts do not imply that a workflow advanced. The initial workflow gate can report `GATE_PASSED` or `HELD` after a durable authority recheck, but this phase has **no native provisioning or workload migration activity**. Real environment inventory, endpoint discovery, policy mapping and migration execution belong to later waves.

## Verification boundary

Focused transport tests cover credential spoofing, exact WSD and job-scope reads, step-up approval, forged approval bodies, self-approval refusal, size limits, portal origin/PKCE handling, CLI requests and role-separated bootstrap. PostgreSQL-backed HTTP tests, an installed-package run behind the target TLS proxy, an actual enterprise IdP/client registration, IAM sync, database restore and Temporal service deployment remain required qualification gates. A local `TestClient` result is not a production authorization certificate.
