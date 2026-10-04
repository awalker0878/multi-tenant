# Current-authority monitoring and authenticated alert delivery

Reviewed 3 October 2026. `hosting-discovery-monitor` composes existing deterministic
freshness monitoring/history with durable delivery attempts and real HTTPS requests
to an explicitly commissioned alert owner. It neither collects inventory nor
authorizes native reads, migration or activation.

## Current service identity and custody

The existing signed IAM directory admits `SERVICE` identities with only exact-scope
`DISCOVERY_MONITOR` grants. Human/worker identities cannot hold that role; a service
cannot hold owner, operator, portfolio or worker grants. JWT role/kind claims remain
ignored. The pinned OIDC verifier checks external issuer/audience/signature and reads
current signed directory/session state on every authorization. Operator HTTP endpoints
still require HUMAN.

The protected file pins subject, organization/tenant, exact registered environments
and native scopes, bounded cadence/freshness policy, token selector and explicit alert
owner. `deploy/discovery/monitor.json.example` is uncommissioned: placeholder CA/key
values fail validation. Duplicate, ambiguous or foreign targets hold. Changes during
work require restart. A commissioned identity agent rotates the protected short-lived
token; this service never extends human sessions or issues identity/enrollment.

| Environment value | Purpose |
| --- | --- |
| `HOSTING_MONITOR_DSN`, `HOSTING_MONITOR_DB_ROLE` | Dedicated live-checked SQL login, one verified TLS host and bounded connection timeout. |
| `HOSTING_DIRECTORY_DSN` | Distinct live-checked directory resolver SQL login. |
| `HOSTING_OIDC_ISSUER`, `HOSTING_OIDC_AUDIENCE`, `HOSTING_OIDC_JWKS_URI` | Existing pinned external identity verification. |
| Existing `HOSTING_EVIDENCE_*` values | Independently retained Object Lock/audit checkpoints and Vault verify-only trust; the monitor tenant must be in the startup scope file. |

Every history/delivery operation rechecks identity, role expiry/revocation, exact
registration and independent evidence custody. DDL and IAM sync use separate credentials.
Migration `0026`, applied after its predecessors, adds immutable scoped
`discovery_alert_deliveries`, forced tenant RLS, no site-worker access, exact original
freshness-check references and guarded sequential transitions.

## Dedicated SQL login

The startup probe refuses superuser/RLS bypass, site-worker membership, mutable tables,
unrelated INSERT/SELECT privileges and missing forced-RLS tables. Commission these
metadata reads and monitoring/audit appends only:

```sql
GRANT USAGE ON SCHEMA hosting_controlplane TO hosting_discovery_monitor;
GRANT SELECT ON hosting_controlplane.environment_registrations,
  hosting_controlplane.discovery_generations, hosting_controlplane.evidence_entries,
  hosting_controlplane.evidence_streams, hosting_controlplane.audit_streams
  TO hosting_discovery_monitor;
GRANT SELECT, INSERT ON hosting_controlplane.discovery_freshness_checks,
  hosting_controlplane.discovery_alert_deliveries, hosting_controlplane.audit_events
  TO hosting_discovery_monitor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA hosting_controlplane TO hosting_discovery_monitor;
```

The login cannot write discovery campaigns/results, registrations, drafts, workloads,
jobs or native leases. Failed targets stay `CHECK_HELD`; unknown coverage remains
unverified. New checks use `FreshnessHistoryRepository`; generation metadata reads
use the existing `DiscoveryRepository`.

## Authenticated owner receipt contract

Protected `alertOwner` configuration alone chooses the receiver. Exact connection IP,
HTTPS hostname, pinned CA bytes, bounded deadlines/responses and a separate protected
receiver token gate transport. No redirects, fallback or automatic POST retry occur.

| Request | Required receiver behavior |
| --- | --- |
| `POST /v1/discovery/alerts` | Accept retained intent; bind its full digest and return a signed current receipt. Exact alert-ID/body retries refer to one logical alert; changed bytes conflict. |
| `GET /v1/discovery/alerts/{alertId}/receipt` | Return current delivery/acknowledgement for that exact historical intent. |

The response is exactly `{ "receipt": {...}, "signature": "<base64 Ed25519>" }`.
Receipt fields: `format` (`hosting-discovery-alert-owner-receipt/1`), `ownerId`,
`receiptId`, `alertId`, `alertDigest`, `checkRecordDigest`, `status`, `acceptedAt`,
`observedAt`, `expiresAt`, `acknowledgedBy`, `acknowledgedAt`. The signature covers
canonical sorted compact ASCII JSON of the receipt. Verification requires the
configured owner's public key, exact retained digests, UTC chronological timestamps,
observation within five minutes and expiry within fifteen minutes of observation.

`DELIVERY_ACCEPTED` establishes owner acceptance with null acknowledgement actor/time.
`ACKNOWLEDGED` requires an identified external owner actor and acknowledgement between
acceptance and observation. Acceptance never invents a human acknowledgement. Commission
an owner that actually delivers/escalates notifications and records on-call decisions;
no email/paging/ITSM product is assumed by these fixtures.

## Durable attempts, scheduling and recovery

Start and audit commit before sending. A session advisory lock excludes overlapping
dispatch across processes while separate start/receipt transactions commit. Interrupted
starts or lost replies remain `DELIVERY_UNKNOWN`. Ordinary cycles reuse exact
slot/check/alert IDs without retrying unknown delivery or resampling original data.
Accepted/acknowledged deliveries are historical on later cycles; explicit GET obtains
a current owner receipt.

```sh
hosting-discovery-monitor cycle --config /etc/hosting/discovery/monitors/tenant-1.json
hosting-discovery-monitor run --config /etc/hosting/discovery/monitors/tenant-1.json --duration-seconds 3600
hosting-discovery-monitor retry-unknown --config /etc/hosting/discovery/monitors/tenant-1.json --environment-id environment-1 --check-id <retained-check-id>
hosting-discovery-monitor refresh-acknowledgements --config /etc/hosting/discovery/monitors/tenant-1.json --environment-id environment-1 --check-id <retained-check-id>
```

Retries require current authority and the same exact retained intent; at most three
POST attempts are allowed. Reconciliation selects an old check explicitly and creates
no new monitoring slot or collection. Revocation after sending may prevent retaining
the receipt; the committed start remains unknown. `notificationAttempted: null` means
current attempt state cannot be proven. A hold does not establish delivery rollback.

The reviewed monitor service/timer in `deploy/discovery/` use installed commands, a
dedicated nonprivileged OS account and protected per-instance environment file. The
timer runs on five-minute UTC boundaries, matching the example's 300-second slots.
Systemd/deterministic IDs prevent a missed/repeated tick from resampling that slot.
`run` is bounded to seven days/cycle limits and observes termination between cycles.
Startup/command failures emit sanitized holds.

## Conversion and acceptance boundaries

B48 must preserve freshness checks, entire delivery-event chains, matching audit
streams and signed directory state. Quiesce old writers before conversion; retain exact
owner/actor/digest bindings and reconcile independent audit/checkpoint and receiver
idempotency state before dispatch resumes. Whole-database rollback is not detected by
in-database hashes alone. Never reset an interrupted start or silently change its owner.

Tests execute actual JWT/signatures, current directory lookups, real TLS POST/GET,
attributed signed acknowledgements, revocation, exact retries and conservative holds.
Isolated PostgreSQL tests cover signed SERVICE enrollment/revocation, dedicated monitor
roles, forced RLS, immutable/audited attempts and session-lock concurrency. Their local
absence is reported as a skip. Installed vendor, enterprise receiver, identity-agent
and on-call qualification remain separate, alongside visibility/privilege reconciliation,
measured estate performance, custody/DR and operating handover.
