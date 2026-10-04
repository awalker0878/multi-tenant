# Governance service

Status: proposed service specification. Runtime: Laravel/PHP; destination: `services/governance/`. Owner: product engineering with IAM/security. ADR-009 selects the actual identity/delegation system and revocation guarantees.

## Purpose and responsibility boundary

Own who may act for a tenant, the resources/actions they may affect and the conditions under which an exact plan is approved. Keep the actor, delegating service and deciding authority attributable throughout a workflow.

Governance is not a password directory, inventory owner, execution engine or evidence qualification authority. Approval permits a defined plan/action/scope under conditions; it does not establish native support, reserve capacity or prove the job executed.

## Owned aggregates and invariants

| Aggregate | Rule |
| --- | --- |
| Tenant | Stable boundary with administrative state, membership and allocation policy. Tenant closure cannot erase retained operational records. |
| Membership / grant | Subject, tenant, permitted action/resource scopes, delegation restrictions, effective/expiry times and revision. No implied authority from a matching name. |
| Authorization decision | Attributable decision and applicable policy/grant versions; validity is explicitly bounded and never inferred from an event alone. |
| Approval | Append-only decision bound to immutable plan ID/digest, action, exact scope, conditions, expiry and approval-policy version. |
| Revocation | New attributable record that invalidates the grant/approval; historical approval is preserved. |
| Break-glass use | Time-bounded exceptional authority with reason, scope, independent review requirements and audited expiry. |

Enforce separation of duties from effective identities, not UI roles alone. Plans and their referenced actors may outlive membership changes; retain accountability while rechecking current authority. Approval for migration does not implicitly authorize later source retirement.

## Proposed API surface

Routes are relative to governance. Tenant administration begins at `POST /v1/tenants`; tenant-specific routes use `/v1/tenants/{tenant_id}`.

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

Initial federation, service trust and bootstrap administrator identity come from a reviewed deployment configuration and controlled bootstrap procedure. Use an explicit one-time operation, not a hard-coded account or universal secret. Verify bootstrap identity through the configured trust root, create the first administrative grant, audit it and disable/restrict further bootstrap use.

Before catalogue integrated acceptance, create the isolated fixture tenant and the minimum application-author/reviewer/operator grants. Real production assignments require the actual tenant administration process. Governance validates service audiences and delegated subject chains; no caller may mint itself an approval role.

Scopes distinguish tenant administration, grants, application authorship, approval, admission and recovery. Scope comparisons use resource identifiers and permitted sets, not substring matching or user-provided labels. Authority to administer one tenant grants no estate-wide inspection privilege.

## Laravel enforcement boundary

Apply the [security and tenant isolation engineering standard](../engineering/security-and-tenancy.md) to every governance route, job and administrative command. Resolve the requested tenant from verified membership/delegation, scope resource binding and queries, then evaluate a named action policy. No administrator `Gate::before` allow-all may bypass that sequence or the approver-independence rule. Owner APIs continue to enforce their own resources even when governance supplies a decision.

Use explicit command validation and writable-field allowlists. Actor identity, tenant ownership, approval disposition, decision revision and audit fields come from verified context and domain transitions; request fields cannot set them directly. Validation of nested grants must reject unexpected authority fields and constrain referenced resources to permitted scope. Responses expose only authorized fields, including for denied, expired or revoked decisions.

Cache decision results only within ADR-009's accepted freshness and revocation bounds, keyed by all relevant actor/service/tenant/action/resource and policy revisions. A cache miss or unavailable mandatory authority check cannot broaden access. Background commands recheck current actor authority; consumers of committed facts validate provenance and their scoped service authority so later actor revocation cannot erase accountability or suppress revocation/audit propagation. Follow the [data and messaging rules](../engineering/data-and-messaging.md). Long-lived Laravel processes must not retain the previous request's tenant, grants or log context. Token abilities, if used, supplement resource policies and are never the sole check for a first-party session.

## Consistency, retries and events

Commit grants/approvals/revocations, command receipts, audit and outbox atomically. Idempotency is scoped by tenant/effective actor/command; same key with a changed digest/scope is a conflict. Grant mutations compare expected revision; concurrent approval/revocation requests preserve a deterministic versioned history.

Publish `governance.tenant.changed`, `governance.grant.changed`, `governance.approval.recorded` and `governance.approval.revoked`. Events notify caches and running jobs; they do not replace current decision checks. Consume catalogue/planning references only as pointers or display projections; fetch the immutable authoritative plan for an approval decision.

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

Owned source root: `services/governance/src/Contexts/Governance/`. Tenant membership/delegation, permission decisions and approval/revocation capabilities, with framework-independent rules and explicit persistence/identity ports.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). Domain, Application, Infrastructure and Interfaces have explicit dependency direction (lowercase equivalents in Python). Framework host composition binds adapters; public API/event schemas define cross-service access. Internal models, use cases and migrations are not exported as shared business packages.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.
