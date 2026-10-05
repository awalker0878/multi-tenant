# Bounded support access

Use [policy version 1](../../implementation/p02-support-access.md) and the
[Governance API contract](../../../contracts/openapi/governance-support-v1.json).
This procedure permits only named membership/grant diagnostics. It creates no
impersonation, general tenant permission, native-write authority or offline login.
There is no Console support screen in this increment. API integration must keep
workload credentials and actor session headers in the trusted server process.

## Before enabling

Apply Governance migrations with the migration owner, then deploy the application.
The runtime role has append/read access to support history and narrowly enumerated
mutable columns; it cannot rewrite immutable request, approval, review, audit or
outbox payload fields. Existing sessions without a retained signing-key fingerprint
must sign in again before support privileges can be requested or approved.

The installation must supply actual accountable tenant/security approvers, a separate
reviewer, case tracking, protected audit custody, retention/sovereignty and incident
response ownership. Record protected references, never credentials, in the operating
record. A synthetic campaign identity is not an appointed production operator.

Provision a protected `support-audit` consumer identity and import/merge the
[restricted topology](../../../deploy/dependencies/stateful/support-notifications.json)
through the broker administration process. The fragment contains no users/passwords;
it grants that pre-existing identity read access only to the `support.audit` quorum
queue. Twelve explicit routes receive support events. Console/tenant identities must
not read this queue. Governance may publish to `governance.events`, but cannot configure
broker topology. Verify TLS, routed publisher confirmation and storage/queue capacity
before enabling the scheduled relay. The repository supplies the publisher and wire
contract; production audit-sink integration and custody remain installation inputs.

## Request, decide and execute

1. A freshly authenticated federated installation administrator appoints a different
   actor to `approver` or `reviewer` for the exact tenant/site/environment via
   `POST /v1/support-security-grants`, with an expiry no more than 30 days and a case
   reference. Tenant administration alone cannot appoint these roles.
2. A current scoped tenant member requests exact actions/resources and a named executor
   at `/v1/tenants/{tenant}/support-access`. Review the returned immutable binding and
   digest. Use a unique idempotency key for each intended command. Case references
   are bounded identifiers; do not put incident narrative or secrets in them.
3. The tenant administrator and security approver separately read the current request
   and `approve` its exact digest/current revision with their own fresh sessions.
   Neither can be requester/executor, and one person cannot satisfy both actor roles.
   A revision conflict requires fetching and reviewing the current state before retry.
4. The named executor signs in freshly, then explicitly `activate`s using the current
   digest/revision. The returned expiry is authoritative and can be shorter than the
   requested lifetime. No returned status or event is a reusable permit.
5. The executor uses `inspect` for one named action/resource and exact site/environment
   with the same session. Ordinary tenant routes remain independently authorized.
   The owner rechecks online trust and current authority and commits the attributable
   admission before returning whitelisted diagnostic data. Another session requires
   a new request; never copy session headers into browser code, tickets or logs.
6. Revoke when finished. The independently appointed reviewer reads the terminal
   request and immutable history, checks every admission, and records `acceptable`
   or `incident` with a review case reference. Review is due within 24 hours of the
   effective expiry; an overdue used request blocks that executor's next activation.

## Denial and containment

On changed binding, role, session, tenant/resource revision or signing material,
stop and examine the current owner status. Detected authority change permanently
invalidates the request; do not edit stored hashes, reset state, extend dates or
replay an old approval as permission. A new request needs new independent approvals.

Issuer/JWKS or encryption-custody outage holds new privileges and inspections.
Current local federated admission still permits an authorized rejection/revocation
and history read, without requiring the failing provider. A recovery admission hold
denies all protected endpoints, including those containment APIs; use independently
controlled infrastructure admission containment. No bootstrap reset or cached-key
fallback is supplied. Recover using the separately reviewed identity custody/resumption
procedure, never by copying the old active admission descriptor with the database.

## Audit and delivery

The scheduler runs `support:expire-access --limit=100` and
`support:publish-outbox --limit=10` each minute. Both accept bounded limits 1–500.
Expiry is checked synchronously too; scheduler availability does not authorize use.
Runtime insert/outbox failure rolls back the admission and prevents diagnostic output.

Events follow [AsyncAPI](../../../contracts/asyncapi/support.yaml) and the
[new event schema](../../../contracts/schemas/events/support-change-v1.json).
They contain internal references, revision, policy revision, correlation UUID, timestamp
and canonical audit hash, without case/scope/session/secret payloads. Receivers deduplicate
by event ID, tolerate unordered/duplicate delivery and use current owner authorization
for any history fetch. A past approval event never grants current rights.

Unconfirmed publication uses bounded exponential backoff with stable event bytes;
malformed facts are quarantined with a redacted error. An unavailable audit store
leaves the claim retryable. Monitor oldest pending age, retries, quarantine, queue
capacity and overdue used requests in the protected operational record. Broker outage
can delay notification while the immutable owner audit/outbox remains durable; it
must not erase facts or rewrite history. Role/session revocation does not suppress
committed history delivery. Retention and external archival require the appointed
custodian's process; runtime has no history deletion operation.

Attributed request denials are bounded to 60 per actor/minute. Saturation returns
429 while preserving any expiry/invalidation transition. Authentication failures,
invalid inputs and undiscoverable requests remain in ordinary redacted request
telemetry and are not falsely attributed to a tenant support request.

The hosted qualification uses disposable PostgreSQL, verified TLS RabbitMQ and
synthetic identities/receivers. Full-schema restore retains terminal requests,
approvals, admissions, reviews and audit/outbox bytes. It does not authorize restored
access, supply an external audit custodian or establish production RTO/RPO.
