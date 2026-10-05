# P02 installation identity event delivery

Owner: Governance/IAM. Packages P02.01/P02.03; requirements R03/R04/R32;
criteria G02.01/G02.03/G02.04; Q01.06/Q01.09/Q01.15. Implementation and
verification remain IN_PROGRESS; this increment does not pass a gate.

## Contract and preserved history

The [identity schema](../../contracts/schemas/events/identity-change-v1.json)
and [AsyncAPI channels](../../contracts/asyncapi/identity.yaml) version the distinct
installation identity outbox. They cover bootstrap, local login/password changes,
OIDC settings/verification/activation, federated login, session revocation and
service delegation issuance/revocation. Tenant notification v1 bytes are unchanged.

Each message has a stable event ID equal to its immutable audit ID, UTC event time,
event type, installation scope, internal actor attribution and audit digest. The
codec verifies the audit/outbox ID, type and timestamp agreement. Federated actors
use internal UUIDs; deployment, bootstrap and unauthenticated events carry a null
actor ID and an explicit kind. Event-specific actor constraints reject malformed
history. No external subject, tenant membership, username, password, session,
client secret, delegation token, provider settings or current permission is sent.

`audit_sha256` hashes UTF-8 compact JSON with fields in this exact order:
`id`, `event`, `actor`, `occurred_at`. The time is UTC `YYYY-MM-DDTHH:MM:SSZ`;
slashes are unescaped. This is the documented canonical projection of the legacy
audit row, not a digest of database storage bytes. The original audit/outbox rows
are preserved. Database failures release the claim and report unavailability;
they must not quarantine valid history.

These installation facts belong to restricted installation consumers. They must
not enter tenant queues or user projections without explicit owner authorization.
They do not identify the exact revoked session or delegation and cannot be used to
infer current authority, reopen access or reconstruct permission state. Consumers
validate the schema and publisher, record event ID and wire digest atomically in
their own durable inbox, reject same-ID/different-byte conflicts, and acknowledge
after commit. Duplicates and reordering are expected. Reconcile through owning APIs
for the approved consumer use case; do not infer ordering from UUIDs or timestamps.

## Delivery and deployment

`identity:publish-outbox --limit=100` uses the same confirmed transport and claim
implementation as tenant events, with an explicitly selected identity table and
codec. PostgreSQL `FOR UPDATE SKIP LOCKED` prevents competing active claims.
Verified TLS, persistent delivery, mandatory routing and broker confirmation are
required. A confirmed message is marked published only in the database commit;
process death or lost acknowledgement may replay the identical wire bytes.

Unconfirmed deliveries retain their immutable fact, sanitized error and bounded
exponential retry delay (two seconds to five minutes). Invalid history is
quarantined without blocking independent facts; no automatic rewrite or deletion
is provided. The command bounds batches to 1–500 and reports aggregate counts.
Retired actors, revoked sessions and provider outages do not suppress committed
facts. Delivery is independent of authorization and login availability.

Apply additive migration `007_identity_event_delivery.sql` after 001–006 with the
Governance migrator. It adds delivery metadata/indexes without altering audit
history or `published_at`; the runtime receives only the additional column-update
privileges. The scheduler invokes a bounded identity batch every minute alongside
tenant publication and approval expiry. The existing restricted `governance.events`
exchange carries distinct `identity.*.v1` routing keys. Bind a separately owned
installation queue before enabling delivery; a tenant-only binding cannot satisfy
identity routing. See the [operations runbook](../operations/runbooks/governance-events.md).

## Verification and remaining scope

The local SQLite feature suite covers existing-row compatibility, all twelve event
types, attribution/schema denials, immutable agreement, missing storage, bounded
batches, delayed retry, quarantine isolation, post-revocation delivery and rollback
replay. Static analysis and dependency boundaries also pass. The hosted event
campaign now runs identity-specific PostgreSQL concurrency, process death after
real TLS confirmation, unchanged duplicate wire, separated routing and untrusted
CA recovery. EV-P02-008 retains the passing campaign at
`1d45f11146913c7401732e9d6be0c8bd7677dfda`: 60 PostgreSQL/TLS broker tests
(854 assertions), five checks, 153 source bindings and ten log hashes.
EV-P02-007 retains nine passing local command logs,
141 Governance tests (1,714 assertions; six real-broker cases skipped), and 158
matching source bindings at `7b24476c71a778dcf9a865b04c13aa35aa8b3992`.
The [workflow observation](../../verification/p02/identity-delivery-regression-runs.json)
records the new queued/pending integration campaigns and superseded cancellations;
none is registered as a pass in that original observation. The
[hosted follow-up](../../verification/p02/identity-delivery-hosted-runs.json) records
the later broker success and Firefox job result. EV-P02-009 retains the Firefox
campaign at `7b24476c71a778dcf9a865b04c13aa35aa8b3992`: 50 checks, 105
PostgreSQL cases (1,542 assertions), two compiled journeys, four HTTPS/PKCE
exchanges, 259 source and six artifact hashes. Chromium/WebKit and the newer-source
broker regression remain queued at that observation. The identity campaign also checks runtime denial
of immutable identity-outbox updates/deletion.

EV-P02-011 retains the newer-source regression at `7b24476` after the cancelled job
was rerun: attempt 2 of run `37367321499` passes the same 60 cases, 854 assertions,
five checks, 153 source bindings and ten log hashes. The
[retrieval record](../../verification/p02/events/run-37367321499-attempt-2/retrieval.json)
binds the original archive and unchanged-source replay. Historical queue snapshots
above remain unchanged.

These relay-only campaigns use synthetic receiving witnesses. The separate
[Console consumer](p02-console-notifications.md) now qualifies five tenant routes;
it excludes installation identity events. Installation consumer ownership,
reconciliation APIs, retention/replay budgets, real alert recipients, operated
custody, HA, independent restore/revocation reconciliation and gate acceptance
remain open. No authority or customer notification is created by this campaign.
