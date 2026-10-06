# Catalogue authoring and event delivery

Scope: the P03 application intent API, Console workspace and committed-fact publisher. The [implementation record](../../implementation/p03-catalogue.md) identifies measured source and limits. This procedure does not claim an operated deployment or pass G01/G02/G03.

## Provision and expand

Use the pinned service images and the existing PostgreSQL owner/runtime/migrator split. Provision the private `catalogue` database, `app` schema owned by `catalogue_owner`, runtime CONNECT/schema USAGE and the dedicated migration identity. Run the service's ordered SQL migrations once through the controlled migrator; `002_catalogue.sql` is additive, transactional and replayable. It has no data rewrite or destructive rollback. Do not give runtime a default grant of UPDATE/DELETE on future tables: the migration grants append-only history and only the mutable version/pointer/publication columns.

Keep old migrations and retained history when rolling application code back. An older foundation binary cannot serve Catalogue v1 commands; route authoring only to the compatible P03 API. Do not down-migrate accepted revisions. Back up and restore application/deployment pointers, immutable revisions, reference versions, workload associations, command receipts, audit and outbox together. Never truncate receipts to clear a retry problem.

Catalogue uses `DB_HOST`, mounted `DB_PASSWORD_FILE`, `DB_SSLROOTCERT` and mandatory `verify-full` TLS. Database and role are fixed as `catalogue` / `catalogue_runtime`. The Console similarly uses its own `console` database and runtime identity. No service receives another service's database credentials.

| Trust boundary | Mounted credential and configuration |
| --- | --- |
| Console → Governance | Console `CONSOLE_CREDENTIAL_FILE`; Governance accepts its independently mounted copy. `GOVERNANCE_URL` and `GOVERNANCE_CA_FILE` identify the trusted HTTPS peer. |
| Console → Catalogue | Console `CATALOGUE_CONSOLE_CREDENTIAL_FILE`; Catalogue `CONSOLE_CATALOGUE_CREDENTIAL_FILE`. Configure `CATALOGUE_URL` / `CATALOGUE_CA_FILE` in Console. |
| Catalogue → Governance | Catalogue `GOVERNANCE_CREDENTIAL_FILE`; Governance `CATALOGUE_GOVERNANCE_CREDENTIAL_FILE`. Configure Catalogue's `GOVERNANCE_URL` / `GOVERNANCE_CA_FILE`. |
| Catalogue → broker | `CATALOGUE_BROKER_HOST`, `CATALOGUE_BROKER_PORT` (default 5671), `CATALOGUE_BROKER_PASSWORD_FILE`, `CATALOGUE_BROKER_CA_FILE`; broker identity `catalogue`, private vhost `product`. |

Browser cookies and Governance user session tokens never reach Catalogue. Console obtains a short audience/action/resource/environment-bound actor delegation for each request. Catalogue verifies it and active service/data owners against current Governance authority. Missing trust, revoked membership, wrong scope or unavailable authority cannot become a fallback grant.

## Run the publisher

Provision [the versioned intent binding](../../../deploy/dependencies/stateful/catalogue-intent.json) with deployment-owned identities and credential hashes. Merge permissions deliberately with existing owner permissions; importing the fragment blindly must not overwrite other required queues. The durable quorum queue `planning.intent` is separate from the P01 foundation demonstration queue. It retains committed facts for P05's future Planning consumer; provisioning a queue does not implement that consumer.

Run `php artisan catalogue:publish-events --limit=100` using the Catalogue runtime identity. Each call handles at most 100 events and exits nonzero on an unavailable or unconfirmed publish. The confirmed publisher has a 2-second connect and 5-second acknowledgement deadline. Its SQL transaction uses a 3-second statement timeout and 15-second idle timeout. Concurrent relays use locked outbox rows and cannot overtake an earlier pending sequence for the same resource.

Assign one operated supervisor/scheduler and a bounded retry policy; use a 1-second initial delay with jitter, capped at 60 seconds, and alert after five consecutive failures or oldest pending age above five minutes as initial development thresholds. Receiving SRE must select its actual schedule, drain deadline, retention and storage/backpressure budget before release. The command does not silently spin or drop a pending event. Stop accepting new authoring through ingress if retained-state capacity is endangered; keep reads available only while their current authorization and database checks succeed.

Inspect non-sensitive counts and oldest pending time through the owned monitoring identity. Diagnose broker/CA/credential/ACL and mandatory-routing failures before rerunning the same command. Never manually mark an uncertain row as published, renumber an event, delete a receipt or republish a changed envelope. A confirmed event can be redelivered after a process interruption; consumers must deduplicate `event_id`, validate producer/tenant/schema and track sequence. An already committed fact still requires delivery after its original actor is revoked. It grants no permission to initiate work.

## Resolve an authoring error

| Result | Operator action |
| --- | --- |
| 422 | Correct the identified field, relationship, owner or graph. A required unsupported control is valid intent; it remains for Planning assessment. |
| 428 / 412 | Load and compare current intent. Adopt the reviewed application ETag explicitly, retain the draft, and publish a new command. |
| 409 | Inspect the existing result and key binding or reference lifetime. A key cannot identify a different action/body/expected revision. |
| Unconfirmed / 503 | Keep the request, ETag and command key unchanged. Retry that exact command after the dependency recovers; an accepted retry returns its original receipt. |
| 403 / changed access | Return to tenant selection. Historical URLs and cached drafts cannot bypass current authority. |

Create/revise commands contain complete intent snapshots. The schema bounds an intent to 256 KiB, 100 workloads, 200 datasets, 500 dependencies and 100 shared-service requirements. Application/reference/history pages return at most 50 items with scoped cursors; an application has at most 100 environment deployment streams. Reference names/zones are stable identities. A referenced current definition cannot retire; previous version bytes remain immutable.

`/health/live` still measures the process only. The frozen foundation `/health/ready` contract remains closed; do not interpret a liveness response or a direct integration request as operated readiness. P01's receiving/deployment readiness work remains explicit. No native platform effect is part of P03 authoring.
