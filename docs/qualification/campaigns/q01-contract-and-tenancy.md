# Q01 — Contract and tenancy

Q01 verifies R02–R06 and the tenant boundary reused by later campaigns. It supports P01.03/P01.05, P02.01–P02.05, P03.01–P03.05 and affected P06 integration work. Its principal review points are G01.03/G01.05, G02.01–G02.04, G03.01–G03.04 and G06.01.

## Scope and ownership

The architecture/quality leads coordinate contract checks; governance and catalogue owners supply authoritative permission and domain rules; security independently reviews denial coverage. E1 covers deterministic schemas and invariants. E2 requires actual PHP/Python services, persistence, broker, identity dependency and browser sessions. This campaign produces no native support claim.

Use the [contract conventions](../../contracts/README.md), [examples](../../contracts/examples.md), [domain model](../../product/domain-model.md) and [governance specification](../../services/governance.md). Select exact API/event versions in the run manifest and record consumer/producer revisions independently.

## Preparation

1. Seed Permit Desk in tenant A and an equivalent application in tenant B, with distinct users, memberships, evidence objects, jobs and search projections.
2. Create requester, approver, auditor and service identities with non-overlapping action/resource grants. Record permitted delegation and separation-of-duties rules.
3. Prepare valid, expired, wrong-audience and wrong-issuer credentials through the approved test issuer. Keep tokens out of committed test reports.
4. Prepare request/event fixtures with exact field types, canonical payload digests, revisions and idempotency keys for both PHP and Python.
5. Capture database state, outbox/inbox counts and role grants through approved observation access before each fault case.

For P02 identity tests, prepare a clean installation with no external OIDC deployment settings, an authorized installer display channel and a test OIDC provider configured only through the console. Capture lifecycle metadata without recording passwords, client secrets or tokens. Include concurrent bootstrap, interrupted display and pre/post-activation restore fixtures.

For P02 approval tests, use synthetic immutable plan fixtures conforming to the agreed P00/P01 interface. P05 producer implementation is not a prerequisite for verifying the approval contract; rerun the binding cases against actual compiled plans when that producer is available.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q01.01 | Round-trip every selected request, response and event through PHP and Python validators; submit unsupported versions and invalid enum/type values | Both languages preserve required meaning; incompatible inputs fail without mutation or delivery | Conformance report and rejected payload digests |
| Q01.02 | Use A's identity with B's known IDs across API, search, export, job, projection and evidence paths | No B data, object URL, count or state leaks; consistent policy denial and attributable audit | Endpoint/role matrix and redacted responses |
| Q01.03 | Forge tenant/actor fields, call as an untrusted service and alter delegated resource scope | Caller assertions do not override authenticated authority; wrong issuer/audience and expired credentials fail | Identity-validation and audit records |
| Q01.04 | Create valid multi-workload/multi-domain intent, then cross-tenant links, dangling references and dependency cycles | Valid model persists; each invalid association is rejected without partial intent or event | Invariant cases and authoritative before/after state |
| Q01.05 | Race two updates from one ETag; retry an accepted command; reuse its idempotency key with changed content | One revision wins; stale edit fails; identical retry returns original result; changed content conflicts | Request timeline, revision chain and record counts |
| Q01.06 | Fail the outbox write inside a mutation transaction; redeliver one committed event repeatedly | Failed transaction creates neither mutation nor event; duplicates create one logical projection/inbox result | Transaction trace and independent DB/inbox observations |
| Q01.07 | Approve a plan, then change digest, action, resource scope or expiry; attempt requester self-approval | Only the exact current scope can be admitted; separation-of-duties failures are visible | Approval-binding matrix and admission denials |
| Q01.08 | Revoke membership/approval and rotate issuer keys; remove the issuer/key dependency | New privileged admission follows selected fail-closed rules; stale grants cannot regain authority after recovery | Revocation timeline, dependency faults and recovery check |
| Q01.09 | Restart catalogue/governance and replay events while exercising audit/history | Immutable revisions and approval history survive; replay does not invent another intent or decision | Restart/replay report and history comparisons |
| Q01.10 | Complete tenant selection, intent revision, conflict recovery and access-denied tasks by keyboard with delegated roles | Authorized tasks finish; errors explain remediation; focus and stale state do not expose unauthorized actions | Browser task observations and accessibility review |
| Q01.11 | Alternate tenants through the same long-lived worker; inject failure, retries, cache hits, raw/bulk queries and file/export requests | Verified context resets on every lifecycle; keys, constraints, resource fields and object paths preserve tenant scope | Process/DB/cache/object observations and denied-field matrix |
| Q01.12 | Test production browser middleware with login rotation, logout, forged origin/host/proxy headers and expired submissions | Selected Laravel 13 request-forgery and session controls hold; no silent command replay or untrusted forwarding influence | Deployed HTTP/browser traces and effective security configuration |
| Q01.13 | Switch tenant during deferred/partial requests and polling; restore a tab/history after logout or revocation | Late old-context responses are rejected; props, caches, remembered data and history do not leak previous scope | Props/history inspection and timed browser transitions |
| Q01.14 | Send nested/extra input and unauthorized resource relationships; trigger both JSON API and Inertia form errors | Only permitted fields mutate or serialize; API errors remain stable and Inertia uses safe scoped error bags | Request/response schemas, persistence checks and browser validation results |
| Q01.15 | Crash after a domain/outbox commit but before publication; revoke the initiating actor before delivery | Relay recovers committed audit/projection/custody facts under valid consumer authority; new commands and protected downloads remain denied | Commit/publish/revocation timeline, consumer records and denial observations |
| Q01.16 | Grow one tenant's data and relationship skew; exercise list/detail/export and stale-revision UI tasks | Query count/time, page/payload and memory stay within reviewed budgets; lazy-loading regressions fail checks and accessibility remains usable | Query plans, measured budgets and keyboard/assistive-technology task review |
| Q01.17 | Deploy without OIDC configuration; repeat and race bootstrap operations, restart replicas and inspect display/custody boundaries | One local administrator; random temporary password displayed once only to the installer; stored hash and required-change state; no credential in shared/retained logs or artifacts and no retry regeneration | Redacted installer events, state counts and protected secret-exposure inspection |
| Q01.18 | Log in with the temporary password; bypass the change screen through routes/APIs; submit the same password; then change it and retry the temporary credential | Only change/logout allowed until a different password is saved; direct API bypass denied, session/CSRF authority rotated, temporary password rejected and restriction survives restart | Browser/API denials, state transitions and redacted session observations |
| Q01.19 | Configure/test OIDC through console; attempt unauthorized edits, invalid discovery/redirect targets, wrong issuer/audience and login without an administrative grant | No file/deployment-value changes; Governance persists authorized settings/secret references only; invalid tests preserve changed-password local setup and secret values are never returned | Authorized/denied setup API observations, configuration revisions and safe response inspection |
| Q01.20 | Activate after verified federated administrator login; reuse local credentials/sessions, remove the IdP, retry deployment and restore older bootstrap state | Atomic activation/retirement revokes local access; IdP loss does not reopen it; retries create no administrator; restore reconciliation holds stale credentials; interrupted setup cannot duplicate grants | Activation/revocation timeline, outage/retry/restore denials and retained state/audit observations |

## Execution and observations

Execute denial cases against every applicable entry path, including direct service calls that bypass the console. A hidden button is not an authorization control. Observe persistence and projection results independently of the command response.

Use [security and tenancy](../../engineering/security-and-tenancy.md), [data and messaging](../../engineering/data-and-messaging.md) and [frontend standards](../../engineering/frontend.md) for Q01.11–Q01.16. Run foundation cases in P01, then complete and rerun the relevant domain/browser cases as P02/P03 surfaces become available. Standard HTTP test shortcuts that disable CSRF, queue/bus fakes and rollback-wrapped database tests cannot substitute for deployed middleware, broker delivery or committed transaction observations.

Pin the approved issuer-unavailability and key-cache behavior before Q01.08. A reviewer must be able to distinguish cached validation within its accepted validity window from unauthorized continuation after revocation. Record actual timing and cache configuration without inventing a universal timeout.

Preserve the original request ordering and identifiers for concurrent tests. A passing final row count cannot conceal a transient cross-tenant disclosure or an event emitted from a rolled-back transaction.

## Pass criteria and evidence

All applicable cases must pass for each selected contract version and exposed surface. No unauthorized data disclosure, duplicate logical intent, invalid association, invalid approval admission or unaudited privileged transition is acceptable. Required accessibility failures remain visible to the product review.

Package fixture digests, service/runtime revisions, contract conformance results, role/surface coverage, authoritative state checks, browser observations and fault timelines under one run ID. Link actual evidence to individual criteria through the [register](../../implementation/delivery-register.yaml), following the [evidence rules](../../implementation/status-model.md).

## Cleanup and reruns

Revoke synthetic credentials and remove test-owned fixtures through authorized APIs; retain required audit/evidence records. Rerun affected cases after authorization, schema, idempotency, transaction, projection or session changes. Treat new search/export/evidence surfaces as new isolation coverage, even when they reuse a common middleware component.
