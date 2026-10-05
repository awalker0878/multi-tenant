# P02 Governance event delivery and approval deadlines

Owner: Governance. Packages P02.02/P02.03/P02.04; requirements R03/R04/R32;
criteria G02.03/G02.04; Q01.06/Q01.09/Q01.15. Development and verification remain
IN_PROGRESS. This increment implements delivery; receiving acceptance is separate.

## Contract and authority

The [versioned event schema](../../contracts/schemas/events/governance-change-v1.json)
and [AsyncAPI channels](../../contracts/asyncapi/governance.yaml) cover tenant,
membership, grant, quota and approval changes. The isolated Governance package
includes the identical schema. Events carry event/tenant/resource IDs, revision,
time, actor attribution and the SHA-256 of the immutable audit payload. They do
not disclose membership subjects, names, reasons, credentials or full plans.

Events are notifications of committed facts. A consumer authenticates the
Governance publisher through its restricted broker topology, validates the schema,
and uses a durable inbox keyed by event ID. The same ID with different bytes is a
conflict. Delivery can repeat and reorder: compare revisions within tenant and
resource family, reconcile gaps through the owning API and never regress a
projection or turn a message into a grant. Current authority is always checked
directly. Actor revocation cannot suppress a previously committed audit fact.

## Durable relay

`governance:publish-outbox --limit=100` claims one pending row in a bounded
PostgreSQL transaction using `FOR UPDATE SKIP LOCKED`. The relay uses verified
TLS, persistent messages, mandatory routing and publisher confirmations.
`published_at` changes only after a routed confirmation. A killed process or lost
database acknowledgement can replay the same event ID and wire bytes. No
exactly-once transport or consumer completion is claimed.

Transient failures preserve the immutable row, record a sanitized failure code,
and delay retry exponentially from two seconds to a five-minute cap. Malformed
or unknown-schema rows enter quarantine; another tenant's valid event can proceed.
There is no silent discard, pruning, payload rewrite or automatic unquarantine.
The operator command reports aggregate published/retry/quarantine counts and fails
when intervention or retry is needed. The [runbook](../operations/runbooks/governance-events.md)
defines process ownership and recovery.

## Expiry

`governance:expire-approvals --limit=100` records elapsed deadlines even when no
session is live, the provider is down or the tenant is suspended. Each approval
uses the same admission lock order as interactive decisions. Its state/revision,
system audit and outbox insertion commit atomically. Concurrent sweeps and reads
cannot duplicate the transition. Rejected/revoked/expired history stays terminal.
The same domain transition handles expiry encountered by an authorized reader.
Request validation already limits the approval deadline to the immutable plan's
validity; expiry never depends on re-fetching the plan owner.

System expiry has a null actor in storage and `actor_kind: system` in the event.
The existing v1 audit projection keeps its published UUID field type by using
the nil UUID as a system sentinel; the immutable payload still contains null.
No federated actor or login authority is created for that sentinel. Published
OpenAPI v1 bytes remain unchanged.

## Deployment and verification

Apply additive migration `005_event_delivery.sql` after 004. It preserves existing
pending events and immutable payloads, adds delivery metadata/indexes and permits
system attribution. Runtime privileges allow only delivery-column updates; audit,
event contents and approval bindings remain protected. PostgreSQL is the deployed
database; the SQLite feature fixture explicitly translates its unsupported DDL.

Laravel's scheduler registers both bounded commands every minute. Operate one
approved scheduler process (or external scheduled invocation), with the same
Governance image and owned database credentials. Database claims also protect
against accidental overlapping processes. Scheduler delay affects notification
timing, never the immediate deadline enforced during admission.

Local tests cover uncertain confirmation, acknowledgement rollback, revocation,
invalid-event quarantine, two-tenant continuation, exact-time/bounded expiry,
terminal-state preservation, schema encoding and atomic rollback. The hosted
`P02 Governance events` campaign adds real PostgreSQL row locks, competing relay
processes, process death after real TLS broker confirmation, duplicate delivery
and a synthetic durable inbox witness, mandatory-route rejection and untrusted-CA
denial/recovery. EV-P02-004 retains the corrected campaign at
`4afcee1d504b8dfb0725d3306f8c2c55eb1f6dce`: 32 tests and 719 assertions, 132
source bindings and ten retained log hashes. EV-P02-005 includes its passing
regression at the delegation source. The receiver is synthetic, not an implemented
product consumer. Initial failures remain in the correction record.

Identity-bootstrap events remain in their distinct identity outbox; this schema
does not relabel them as tenant events. Actual consumer wiring, retention/replay
budgets, alert receiving, whole-store recovery, HA and operating custody remain
their named receiving and later-service inputs.

Protocol references: [RabbitMQ reliability](https://www.rabbitmq.com/docs/reliability),
[publisher confirmations](https://www.rabbitmq.com/docs/confirms), and
[PostgreSQL row-locking clauses](https://www.postgresql.org/docs/16/sql-select.html).
