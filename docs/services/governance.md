# Governance service

Status: P02 local administrator, first-login password change and session authority are implemented in the [bootstrap increment](../implementation/p02-local-bootstrap.md). Console-managed external OIDC and verified handover are implemented in the [federation increment](../implementation/p02-federation.md); tenant authority and plan-bound approvals are implemented in the [tenancy increment](../implementation/p02-tenancy-and-approvals.md); the increment does not complete P02 or pass G02. Runtime: Laravel/PHP; source: `services/governance/`. Owner: product engineering with IAM/security. ADR-009 defines the identity baseline and remaining delegation checkpoints.

The [package replay](../implementation/p01-laravel-foundations.md) and [image measurements](../implementation/p01-laravel-images.md) bind actual source, dependency and execution results. Diagnostic liveness does not establish application readiness; readiness remains HTTP 503 until real dependencies and their probes are implemented.

## Purpose and responsibility boundary

Own who may act for a tenant, the resources/actions they may affect and the conditions under which an exact plan is approved. Keep the actor, delegating service and deciding authority attributable throughout a workflow.

Governance owns the single installation bootstrap administrator and external identity connections; it does not provide a general-purpose password directory, inventory, execution engine or evidence qualification authority. Approval permits a defined plan/action/scope under conditions; it does not establish native support, reserve capacity or prove the job executed.

## Owned aggregates and invariants

| Aggregate | Rule |
| --- | --- |
| Bootstrap administrator | Installation-local identity, password hash, mandatory-change state and retirement at verified OIDC activation; scoped grants never bypass policy. |
| Identity connection | Revisioned external OIDC settings, secret references, claim mappings and tested activation state; administered through the console and Governance APIs. |
| Tenant | Stable boundary with administrative state, membership and allocation policy. Tenant closure cannot erase retained operational records. |
| Membership / grant | Subject, tenant, permitted action/resource scopes, delegation restrictions, effective/expiry times and revision. No implied authority from a matching name. |
| Authorization decision | Attributable decision and applicable policy/grant versions; validity is explicitly bounded and never inferred from an event alone. |
| Approval | Append-only decision bound to immutable plan ID/digest, action, exact scope, conditions, expiry and approval-policy version. |
| Revocation | New attributable record that invalidates the grant/approval; historical approval is preserved. |
| Break-glass use | Time-bounded exceptional authority with reason, scope, independent review requirements and audited expiry. |

Enforce separation of duties from effective identities, not UI roles alone. Plans and their referenced actors may outlive membership changes; retain accountability while rechecking current authority. Approval for migration does not implicitly authorize later source retirement.

## API surface and remaining integration

Implemented endpoint schemas and limits are in the [tenant](../../contracts/openapi/governance-tenancy-v1.json) and [approval](../../contracts/openapi/governance-approvals-v1.json) contracts. [Data-facing actor delegation](../implementation/p02-service-delegation.md) now provides bounded issuance, target-service resolution and explicit revocation. Native delegation and support/break-glass remain integration work. Routes are relative to governance. Tenant administration begins at `POST /v1/tenants`; tenant-specific routes use `/v1/tenants/{tenant_id}`.

| Method and route | Contract |
| --- | --- |
| `GET /memberships` / `POST /grants` | Authorized administration; write requires retry identity and scope validation; updates use revision preconditions. |
| `POST /authorization-decisions` | Evaluate authenticated effective actor/service against requested action/resource scope; caller cannot supply a trusted actor merely in JSON. |
| `POST /approvals` | Fetch/check exact immutable planning record; validate digest, action, scope, conditions and approver independence; persist `201` with approval ID. |
| `GET /approvals/{id}` | Return authorized immutable decision plus current effective/revoked/expired disposition. |
| `POST /approvals/{id}/revocations` | Attributable, idempotent revocation with reason; no deletion of historical approval. |
| `POST /admission-authorizations` | Evaluate current grant, approval, plan digest/action/scope and validity for lifecycle; bind result to admission identity and configured short expiry. |

Authorization denial is distinguished from unavailable authority internally; external errors follow resource-existence protection rules. Admission authorization is not a distributed lock on governance state. ADR-009 must define freshness bounds and revalidation before each privileged effect; lifecycle records the decision it used and does not ignore revocation races.

## Bootstrap and authenticated scopes

The [ADR-009 identity baseline](../decisions/adr-009-identity-delegation-and-authorization.md) uses console-managed external OIDC and one installation-local bootstrap administrator. A controlled deployment operation creates that identity and its scoped administrative grant exactly once, generates a cryptographically random temporary password, displays it once to the authorized installer and stores only its hash with mandatory-change state. Deployment retries and replicas cannot recreate the identity or reset its password.

Governance authenticates the local account and enforces the mandatory first-login password change across all protected interfaces. Until the change succeeds, only password change and logout are permitted. Reject reuse of the temporary password, rotate session authority and audit the change without credential values. Once changed, the administrator can use authorized console setup functions; normal tenant and separation-of-duties rules still apply.

Governance owns the OIDC connection settings, claim mappings, activation state and scoped secret references. The console presents create/edit/test/activate operations through authenticated owner APIs. Provider settings are application data, not deployment configuration. Secret input is write-only and goes to protected server-side custody; responses expose status/reference metadata only. Workload/service trust remains independently provisioned.

Keep local setup available until a tested OIDC connection proves that an explicitly granted federated administrator can sign in. Atomically activate federation, disable local authentication and revoke all local sessions/delegation. A failed setup test leaves the changed-password account usable; an OIDC outage after activation cannot re-enable it. Persist bootstrap/activation state and reconcile retirement on restore before reopening access. Follow [identity and trust](../operations/identity-and-trust.md) for the complete lifecycle.

Before catalogue integrated acceptance, create the isolated fixture tenant and the minimum application-author/reviewer/operator grants. Real production assignments require the actual tenant administration process. Governance validates service audiences and delegated subject chains; no caller may mint itself an approval role.

Scopes distinguish tenant administration, grants, application authorship, approval, admission and recovery. Scope comparisons use resource identifiers and permitted sets, not substring matching or user-provided labels. Authority to administer one tenant grants no estate-wide inspection privilege.

## Laravel enforcement boundary

Apply the [security and tenant isolation engineering standard](../engineering/security-and-tenancy.md) to every governance route, job and administrative command. Resolve the requested tenant from verified membership/delegation, scope resource binding and queries, then evaluate a named action policy. No administrator `Gate::before` allow-all may bypass that sequence or the approver-independence rule. Owner APIs continue to enforce their own resources even when governance supplies a decision.

Use explicit command validation and writable-field allowlists. Actor identity, tenant ownership, approval disposition, decision revision and audit fields come from verified context and domain transitions; request fields cannot set them directly. Validation of nested grants must reject unexpected authority fields and constrain referenced resources to permitted scope. Responses expose only authorized fields, including for denied, expired or revoked decisions.

Cache decision results only within ADR-009's accepted freshness and revocation bounds, keyed by all relevant actor/service/tenant/action/resource and policy revisions. A cache miss or unavailable mandatory authority check cannot broaden access. Background commands recheck current actor authority; consumers of committed facts validate provenance and their scoped service authority so later actor revocation cannot erase accountability or suppress revocation/audit propagation. Follow the [data and messaging rules](../engineering/data-and-messaging.md). Long-lived Laravel processes must not retain the previous request's tenant, grants or log context. Token abilities, if used, supplement resource policies and are never the sole check for a first-party session.

## Consistency, retries and events

Commit grants/approvals/revocations, command receipts, audit and outbox atomically. Idempotency is scoped by tenant/effective actor/command; same key with a changed digest/scope is a conflict. Grant mutations compare expected revision; concurrent approval/revocation requests preserve a deterministic versioned history.

The implemented outbox records `governance.tenant.changed`, `governance.membership.changed`, `governance.grant.changed`, `governance.grant.revoked`, `governance.quota.changed` and `governance.approval.{requested,approved,rejected,revoked,expired}`. The [Governance relay](../implementation/p02-governance-events.md) publishes schema-validated minimal references with routed broker confirmation, retry/quarantine state and stable event identities. Background expiry records a system transition independently of user sessions. Real receiving-service integration remains phase-specific. Events notify caches and running jobs; they do not replace current decision checks. Consume catalogue/planning references only as pointers or display projections; fetch the immutable authoritative plan for an approval decision.

A plan needs explicit action/scope/expiry semantics. Governance does not approve a mutable “latest plan” alias. Any digest mismatch, changed effect scope, expired plan or missing required approval condition rejects approval/admission. Clock validity follows a monitored trusted-time policy with maximum permitted skew selected before native operations.

## Dependencies, failures and operations

Dependencies: trusted identity, governance database, planning for exact-plan verification, time and configured event transport. Identity or governance decision failure prevents new privilege grants and admissions. Broker failure retains revocation events in the outbox; direct authority checks remain necessary. A planning outage prevents new approvals where immutable-plan verification cannot be completed.

Run with isolated database/service roles and restricted administrative endpoints. Measure authorization latency/error rate, revoked/expired decision use, approval backlog, outbox age and clock skew. Retain tamper-evident audit under approved retention; never log bearer credentials. Restore must reconcile revocations and authority epochs before reopening native admission; restoring an old database must not resurrect grants.

RPO/RTO, decision freshness bounds, break-glass process and independent review owners remain P00.05/P02 decisions. They must be documented and tested before P06/P07 gates; no availability target here overrides fail-closed authority.

## Verification and delivery

P02.01–P02.04 deliver authentication/tenancy/authorization/approval; P05.06 exact admission contract and P06.03 effect-boundary rechecks integrate lifecycle. Requirements R03/R04/R14/R16/R25/R31/R32; campaigns Q01/Q03/Q04/Q09.

Test forged tenant/subject/service audience, excessive delegation, grant expiry/revocation, duplicate decision, same-key changed digest, self-approval where forbidden, plan scope widening, expired approval, retirement under migration approval, authority outage and restore of previously revoked grants. Record deny and allow behavior for two tenants and independent author/reviewer/operator identities.

Include known cross-tenant object IDs, bulk and nested relationships, forged writable privilege fields, stale cached decisions, revocation between enqueue and execution, and alternating tenants in one worker process after an exception. Inspect persisted history, outbox and audit independently of the response. Browser identity acceptance additionally exercises real request-forgery/session middleware and hostile host/proxy headers; a hidden action or test-mode middleware bypass provides no authorization evidence.

## Context source ownership and code control

Owned source root: `services/governance/app/`. Tenant membership/delegation, permission decisions and approval/revocation capabilities. Eloquent models may own approval and grant transition invariants. Actions authorize the actor and coordinate direct Eloquent persistence in local transactions; identity-provider integrations use explicit dependency contracts.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). This service owns its own `App\` namespace. Organize business behavior in `app/Domain/<Capability>/` and use cases in `app/Application/<Capability>/Actions/`, with `handle()` as the Action entrypoint. Keep external adapters in `app/Infrastructure/` and controllers, requests, jobs, listeners, policies and providers in normal Laravel directories. Domain code cannot depend on Application or Infrastructure; Eloquent and Laravel facilities remain available under [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md). Same-context capabilities may collaborate directly; repositories and DTOs require a concrete reason. Public API/event schemas define cross-service access, and internal models, use cases and migrations remain private.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.
