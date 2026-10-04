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

## Execution and observations

Execute denial cases against every applicable entry path, including direct service calls that bypass the console. A hidden button is not an authorization control. Observe persistence and projection results independently of the command response.

Pin the approved issuer-unavailability and key-cache behavior before Q01.08. A reviewer must be able to distinguish cached validation within its accepted validity window from unauthorized continuation after revocation. Record actual timing and cache configuration without inventing a universal timeout.

Preserve the original request ordering and identifiers for concurrent tests. A passing final row count cannot conceal a transient cross-tenant disclosure or an event emitted from a rolled-back transaction.

## Pass criteria and evidence

All applicable cases must pass for each selected contract version and exposed surface. No unauthorized data disclosure, duplicate logical intent, invalid association, invalid approval admission or unaudited privileged transition is acceptable. Required accessibility failures remain visible to the product review.

Package fixture digests, service/runtime revisions, contract conformance results, role/surface coverage, authoritative state checks, browser observations and fault timelines under one run ID. Link actual evidence to individual criteria through the [register](../../implementation/delivery-register.yaml), following the [evidence rules](../../implementation/status-model.md).

## Cleanup and reruns

Revoke synthetic credentials and remove test-owned fixtures through authorized APIs; retain required audit/evidence records. Rerun affected cases after authorization, schema, idempotency, transaction, projection or session changes. Treat new search/export/evidence surfaces as new isolation coverage, even when they reuse a common middleware component.
