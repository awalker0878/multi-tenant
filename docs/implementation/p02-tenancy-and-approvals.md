# P02 tenant authority and plan-bound approvals

Governance owns this increment for P02.02/P02.03/P02.04, R03/R04/R32 and
G02.01–G02.04. Console tenant navigation belongs to P02.05. It extends the
[identity handover](p02-federation.md); P02 development and verification remain
IN_PROGRESS. It does not pass G01/G02 or authorize native execution.

## Tenant ownership and current authority

An authenticated installation administrator can create a tenant and explicitly
assign its initial administrator by exact subject at the active issuer. Creation
does not implicitly make the installation administrator a member. Every tenant
read and command resolves the Console workload credential and a current federated
session; local setup accounts have no tenant authority. Browser role, actor and
selected-tenant values never become trusted authority.

Memberships bind one actor to one tenant, role, optional site/environment scope,
expiry and revision. An absent or revoked membership and an unknown tenant return
the same 404. A tenant suspension blocks access except the current administrator's
reactivation command. Tenant metadata is visible to current scoped members; broader
administrative projections require unscoped administrative authority. The last
active unscoped administrator cannot be removed or made temporary/scoped without
another current administrator. Tenant records and history are never deleted by
these APIs.

| Role | Default actions |
| --- | --- |
| Tenant administrator | Tenant metadata/lifecycle, membership and grant administration, quota read/write, audit read |
| Author | Tenant/quota/application/plan read, application write, plan creation, approval request |
| Reviewer | Tenant/quota/application/plan/evidence read, approval decision and revocation |
| Operator | Tenant/quota/application/plan/evidence read, operation admission observation |
| Reader | Tenant/quota/application/plan/evidence read |

All other actions, including support/break-glass and installation-wide tenant
access, are denied. Delegated grants name one application/plan/approval/operation/
evidence action and cannot delegate administrative or support authority. Each grant
is within its membership's site/environment scope, may narrow to one resource,
expires within thirty days and binds the membership revision. Missing requested
scope cannot match a restricted grant. Membership changes invalidate old grants;
regranting access does not revive approvals based on the previous authority.

Quota entitlement has independent `vcpu`, `memory_mib`, `storage_gib` and `workloads`
limits and a revision. Observed capacity and reservations remain separate and are
returned as unavailable (`null`), never derived from entitlement.

## Commands, concurrency and persistence

The [tenant HTTP contract](../../contracts/openapi/governance-tenancy-v1.json)
requires `Idempotency-Key` for mutations and expected revisions for edits. Receipts
are scoped by tenant/installation, effective actor and command. A repeat with the
same payload returns the committed result only after checking current authority;
changing the payload under that key conflicts. State, receipt, immutable audit and
outbox insertions commit together; an outbox error rolls the command back.

The bootstrap sentinel is the common admission lock, followed by tenant/resource
locks. This deliberately serializes commands against handover and revocation in
this increment. It is conservative; distributed throughput or high availability
has not been qualified. Protected decisions are uncached and marked
`observation_only`. Other resource-owning APIs and the native effect boundary must
still verify their own workload identity, actor delegation, resource and current
admission conditions. A returned JSON decision is not a transferable permit.

Apply `003_tenancy.sql` and `004_approvals.sql` after the identity migrations with
the controlled migrator. Runtime roles cannot delete tenants/memberships/grants,
rewrite or delete audit/receipts, or rewrite immutable approval bindings. Outbox
publication is pending; persisted rows alone are not evidence of transport delivery.
Quarantined restore must reconcile revocations before opening admission. This
increment adds no recovery bypass or support impersonation path.

## Approval policy v1

The [approval HTTP contract](../../contracts/openapi/governance-approvals-v1.json)
fetches an exact immutable Planning revision through the
[consumer binding contract](../../contracts/openapi/planning-immutable-plan-v1.json).
The record binds plan ID/revision/digest, tenant, action, site, environment, resource,
requestor, explicit executor actor IDs and validity. Digest calculation sorts object
keys recursively, preserves array order and hashes compact UTF-8 JSON without
escaped slashes, excluding `digest`. Binding strings are ASCII; numeric fields are
integers. This is a restricted binding format, not a general JSON canonicalization
standard. Extra/missing fields, a wrong digest or a mutable alias are rejected.

Requests must come from the bound requestor with current scoped permission and
expire within twenty-four hours and the plan's validity. A current independent
reviewer may approve or reject; the requestor and named executors cannot do either.
Approval re-fetches the authoritative immutable plan. An approved decision may be
revoked; rejection and revocation do not require a functioning Planning service.
Each transition compares revision and appends history. There is no break-glass
transition. Expiry is immediately effective by time and recorded once when an
authorized reader or validator accesses the record; background expiry publication
is not implemented.

Validation requires the exact plan/digest/action/scope, a named executor with current
`operation.admit`, an unchanged authoritative plan, and unchanged requestor/reviewer
membership and grant fingerprints. A revoked/expired approval or changed authority
cannot be reused after a regrant. The immutable decision history remains readable
to currently authorized readers. Validation is an admission observation, not native
execution authority or an executed result.

`PlanningPlanSource` uses the deployment's internal Planning URL, mounted workload
credential and verified TLS trust, with no redirects and a bounded timeout. These
are service connectivity inputs, not OIDC settings. The real producer is P05.04;
missing connectivity returns 503, with no synthetic fallback in product code.
P02 feature tests explicitly inject a synthetic plan owner as the phase allows.

## Console journey and verification boundary

The Console lists only current memberships, clears prior Inertia history, loads
each selected tenant through Governance, and returns revoked/guessed tenants to
the current account page. Tenant administrators can create/change/revoke scoped
memberships, change quotas and suspend/reactivate access. Every mutation passes
real CSRF middleware and rechecks owner authority. Forms preserve command identity
for retries; stale revisions produce a reload/review error. Secrets and user tokens
remain outside page props. Keyboard navigation receives page/error focus; a full
assistive-technology and multi-tab/late-response campaign remains open.

The local suites cover two-tenant isolation, scoped role/grant decisions, expired
and revoked authority, revision conflicts, idempotency, last-administrator
protection, quota separation, independent audit history and atomic rollback.
Approval cases include self/executor decisions, changed binding fields, plan-owner
outage, expiry/revocation and authority loss/regrant. Console tests cover safe
projections, manipulated role inputs, revoked navigation and real request forgery.
These results are separate from hosted PostgreSQL/browser observations, which must
be retained with their exact source/artifact bindings before evidence is claimed.

Remaining P02 integration: service-to-service actor delegation and owning-service
admission; approved support/break-glass contracts and implementation; durable outbox
delivery/background expiry; deployed recovery/revocation epochs; full browser and
accessibility qualification. Lists are currently bounded to 200 rows (audit 100)
without pagination. No native effect, real provider interoperability, complete
operational acceptance or completed phase is inferred.

## Retained campaign

EV-P02-003 records the passing 44-check campaign, 55 PostgreSQL feature cases
(952 assertions), two compiled browser journeys and verified source/artifact
hashes. The initial timing failure remains retained separately. The full local
suites pass 91 Governance and 76 Console cases; types, dependency boundaries,
formatter, compiled frontend and the five P02 OpenAPI specifications pass.
The [G02 engineering assessment](../qualification/gate-reviews/g02-engineering-assessment-2026-10-05.md)
separates these observations from remaining integration and receiving work.
