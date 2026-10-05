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
rewrite or delete audit/receipts, or rewrite immutable approval bindings. [Outbox delivery](p02-governance-events.md) now uses routed broker confirmations
and retryable database claims; hosted transport observations are recorded separately.
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
transition. Expiry is immediately effective by time and recorded once by an authorized
reader/validator or the bounded background sweeper. System expiry and its outbox
event commit atomically; it needs no live user or available plan provider.

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
remain outside page props. Keyboard navigation receives page/error focus.

Successful sign-out broadcasts only an invalidation signal to same-origin tabs,
with a storage-event fallback. Receiving tabs cancel requests, clear cached Inertia
pages/history, hide the old view and load the login route. No actor, tenant or
credential crosses the channel. A protected page restored from the browser's
back/forward cache reloads through server authentication. If browser policy blocks
both channels, current server checks still apply on the next request; immediate
cross-tab clearing is not guaranteed in that configuration.

The compiled browser campaign holds an old tenant response until a newer tenant
navigation completes, checks that the selected page/focus/quota remain correct,
checks independent unsaved forms in same-session tabs and signs out both tabs.
Actual browser back/forward-cache interoperability, broader supported browsers
and manual assistive-technology qualification remain open.

The local suites cover two-tenant isolation, scoped role/grant decisions, expired
and revoked authority, revision conflicts, idempotency, last-administrator
protection, quota separation, independent audit history and atomic rollback.
Approval cases include self/executor decisions, changed binding fields, plan-owner
outage, expiry/revocation and authority loss/regrant. Console tests cover safe
projections, manipulated role inputs, revoked navigation and real request forgery.
These results are separate from hosted PostgreSQL/browser observations, which must
be retained with their exact source/artifact bindings before evidence is claimed.

The [data-facing delegation and Catalogue guard](p02-service-delegation.md)
implement the initial short-lived service contract. Remaining P02 integration:
real owning-service resources and cross-service wire qualification; approved support/break-glass contracts and implementation; real consumer integration and receiving of outbox/expiry; deployed recovery/revocation epochs; full browser and
accessibility qualification. The [new directory APIs](p02-directory.md) page Console tenants and memberships.
Published v1 lists keep their 200-row bound (audit 100). No native effect, real provider interoperability, complete
operational acceptance or completed phase is inferred.

## Retained campaign

EV-P02-003 retains the preceding tenancy/approval baseline. EV-P02-004/005 add
confirmed event delivery, background expiry and bounded service delegation.
EV-P02-006 retains the latest 47-check campaign: 80 PostgreSQL feature cases
(1,427 assertions), two compiled browser journeys including controlled late
responses and same-session tab sign-out, four HTTPS/PKCE exchanges, six artifact
hashes and 248 source bindings. No browser case is skipped, retried or failing.
Historical failures remain retained separately. At the delegation source the
full local suites pass 116 Governance cases (three real-broker cases are exercised
in the separate hosted campaign), 50 Catalogue and 76 Console cases. The latest
Console type, boundary and compiled-build checks also pass.
The [G02 engineering assessment](../qualification/gate-reviews/g02-engineering-assessment-2026-10-05.md)
separates these observations from remaining integration and receiving work.

## Independent browser engine campaigns

The P02 identity workflow runs the existing two compiled browser journeys in
separate Chromium, Firefox and WebKit jobs. Each has its own fresh PostgreSQL
service, deployment credential, Console/Governance processes and synthetic HTTPS
OIDC provider. Federation activation in one job cannot pre-initialize another.
Each job retains engine-labelled evidence, the exact source, engine identity and
zero-skip/zero-retry checks; one engine failure cannot cancel the other observations.

This extends measurement of first-login change, OIDC handover, tenant navigation,
controlled delayed responses, quota persistence, revoked access and same-session
tab sign-out. A configured matrix is not a passing result. Retain and inspect each
engine report before claiming interoperability. Playwright engine builds do not
establish a managed enterprise browser floor, real back/forward-cache eligibility
or manual assistive-technology acceptance; those remain their receiving tasks.

EV-P02-009 retains the Firefox 155.0 job at
`7b24476c71a778dcf9a865b04c13aa35aa8b3992`: 50 checks, 105 PostgreSQL cases
(1,542 assertions), both compiled journeys, four verified HTTPS/PKCE exchanges,
259 matching source and six artifact hashes. The separately retained
[hosted observation](../../verification/p02/identity-delivery-hosted-runs.json)
records Chromium/WebKit still queued; Firefox success does not qualify those engines.
