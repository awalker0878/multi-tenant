# Governance notifications and approval expiry

Owner: Governance/SRE. Scope: P02 committed tenant and approval notifications.
Use [the implementation record](../../implementation/p02-governance-events.md)
for contract and evidence boundaries. These commands grant no native authority.

## Install and operate

1. Apply Governance migration 005 through its controlled migrator after 001–004.
   Retain the database and custody material under the approved recovery process.
2. Provision a durable `governance.events` topic exchange in the `product` broker
   vhost. Grant the `governance` principal write access only to that exchange,
   with no configure/read permission. Each approved receiving service owns its
   durable queue, routing bindings, least-privilege reader and inbox. Absence of
   all matching bindings must fail publication rather than discard a fact.
3. Mount the publisher password and trusted CA; set `GOVERNANCE_BROKER_HOST`,
   `GOVERNANCE_BROKER_PORT` (5671 by default),
   `GOVERNANCE_BROKER_PASSWORD_FILE`, `GOVERNANCE_BROKER_CA_FILE`. The client
   verifies the certificate and hostname. These are workload transport settings;
   OIDC provider settings still belong exclusively to the Console.
4. Operate `php artisan schedule:work` as a separately supervised Governance
   process, or invoke the two bounded commands from one external scheduler.
   Do not enable both ownership paths. A scheduler replica uses the identical
   image, app configuration, runtime database role and mounted broker custody.
   Drain/replace this process during upgrades.
5. Observe exit status, pending age, retry count and quarantine count. The
   receiving route, polling cadence and alert thresholds require OP03/OP05.
   A broker acknowledgement proves receipt by the broker, not consumer completion.

## Outage and replay

Broker, TLS, credential and unroutable-message failures leave records pending.
Repair the connection/trust/bindings and run
`php artisan governance:publish-outbox --limit=100`; backoff caps at five minutes.
Credential files are read for each publication, so replacing custody takes effect
without a process restart. Rotate both broker and mounted identity through the
approved operating procedure; do not pass secrets on command lines.

For quarantined rows, compare the immutable audit/outbox bytes with their recorded
schema and deployed source. Repair a codec/deployment mismatch through review and
qualification. An authorized migrator may clear quarantine only after documenting
why the original bytes now validate; do not edit event IDs, payloads or history.
No automatic repair or skip rule is supplied.

Process death after broker confirmation may duplicate delivery. Consumers verify
the event ID and byte digest in one local transaction with their projection,
then acknowledge transport. Retain inboxes across the approved replay horizon.
Never reconstruct current permissions from a historical event or reopen an
expired approval during replay. Quarantined restore remains closed to admission
until the separate authority/revocation reconciliation process completes.

`php artisan governance:expire-approvals --limit=100` catches up expired records
independently of broker health and user sessions. Repeat until it reports zero.
The direct admission path already rejects elapsed deadlines; a delayed sweep is
an audit-publication backlog, not an extension of authority.
