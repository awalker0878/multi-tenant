# Durable isolated simulation

Use this P06 procedure only for an independently approved isolated campaign.
Lifecycle refuses operational plans. Native credentials, endpoints and application
datasets have no place in this deployment. Preserve the diagnostic probes'
explicit foundation-readiness limits; verify actual authenticated dependencies
and the campaign separately.

## Install the owned components

Use independently built, locked Lifecycle, Lifecycle worker, Governance, Planning,
Assurance and Console artifacts. Runtime roles do not run migrations. Establish the owned schema and grant runtime
`USAGE` on it without schema creation authority. Apply each
service's ordered SQL as its owning migrator, including Governance migration 013,
Lifecycle migrations 001–003, worker simulation migration 001 and Assurance
migration 001. The simulator owns a separate database/schema and receives no
Lifecycle database access. Assurance runtime cannot update/delete evidence.

The control API starts with `lifecycle-serve`. Start the separate Temporal process
with `lifecycle-workflows`. Start the independent effect owner with
`lifecycle-simulator`; it binds verified TLS on loopback port 8449. Its mounted
`SIMULATION_TLS_CERT_FILE` and `SIMULATION_TLS_KEY_FILE` must match the configured
simulator URL. The image's default health command does not start either worker.

Every PostgreSQL connection requires `DB_SSLMODE=verify-full`, an absolute
`DB_SSLROOTCERT`, owned database/user and mounted `DB_PASSWORD_FILE`. Configure
`TEMPORAL_TARGET`, `TEMPORAL_NAMESPACE`, absolute `TEMPORAL_CA_FILE`, optional
verified `TEMPORAL_SERVER_NAME` and mounted `TEMPORAL_CREDENTIAL_FILE`. Use a
namespace identity with only its needed read/write/worker permissions, separate
from schema administration. No unauthenticated or plaintext fallback exists.

Every owner URL uses verified HTTPS and an absolute CA mount. Supply distinct
credentials for every directed service link:

| Consumer | Required configuration |
| --- | --- |
| Lifecycle | `GOVERNANCE`, `PLANNING`, `SIMULATOR`, `ASSURANCE`, `ALERTS` each need `_URL`, `_CA_FILE` and `LIFECYCLE_{OWNER}_CREDENTIAL_FILE`. |
| Lifecycle callers | `LIFECYCLE_CONSOLE_CALLER_FILE`, `LIFECYCLE_SIMULATOR_CALLER_FILE`, `LIFECYCLE_ASSURANCE_CALLER_FILE`. |
| Governance / Planning | `LIFECYCLE_GOVERNANCE_CREDENTIAL_FILE` / `PLANNING_LIFECYCLE_READER_CREDENTIAL_FILE`, alongside their existing owner links. |
| Simulator | `LIFECYCLE_URL`, `LIFECYCLE_CA_FILE`, `SIMULATOR_LIFECYCLE_CREDENTIAL_FILE`, `LIFECYCLE_SIMULATOR_CREDENTIAL_FILE`, `ASSURANCE_SIMULATOR_CREDENTIAL_FILE`. |
| Assurance | `LIFECYCLE`, `SIMULATOR`, `GOVERNANCE` URL/CA pairs and `ASSURANCE_{OWNER}_CREDENTIAL_FILE`; `LIFECYCLE_ASSURANCE_CREDENTIAL_FILE` and `CONSOLE_ASSURANCE_CREDENTIAL_FILE` authenticate callers. |
| Console | `LIFECYCLE_URL`, `LIFECYCLE_CA_FILE`, `CONSOLE_LIFECYCLE_CREDENTIAL_FILE`, `ASSURANCE_URL`, `ASSURANCE_CA_FILE`, `CONSOLE_ASSURANCE_CREDENTIAL_FILE`, plus its existing Governance session link. |

## Commission one simulation campaign

1. Record source revision, installed service/image versions, namespace, tenant,
   site, plan digest, approval, executor, independent cleanup owner and endpoint
   scope. Mount the exact 40-character source revision as
   `LIFECYCLE_SOURCE_REVISION`; a changed source holds unfinished effects.
2. The custody owner establishes one UUID in independently controlled
   `LIFECYCLE_CUSTODY_EPOCH_FILE` and `SIMULATION_CUSTODY_EPOCH_FILE`. As database
   owner, establish the matching `app.execution_control` row with `id=1` and
   `quarantined=false`. Runtime has no authority to change that row.
3. Mount `LIFECYCLE_SIMULATION_CAMPAIGNS_FILE` read-only: at most 512 KiB,
   `schema_version: 1`, and `records`. Each record includes exact scope, current
   input/artifact digests, simulation-only reservation receipts and safety facts.
   Its campaign binds `id`, `adapter: p06-simulator-v1`, current epoch,
   `worker_ids: [sim-worker]`, action/method/installed tuple/plan digest/actor,
   isolated-lab class, one configured simulator endpoint, credential/data scopes,
   cleanup owner, expiry, revocation and effect budget. This is independently
   approved simulation authority, not Console-supplied owner truth. See the
   campaign builder in `scripts/p06/live_execution.py` for the complete E2 shape.
4. Obtain a new exact-plan approval from the independent reviewer. Verify the
   Console's selected tenant/site/application/environment and simulation label.
   Enter approval and campaign references and admit. If the reply is uncertain,
   recover the unchanged command receipt; do not create a new command identity.

## Handle held work and alerts

Read the authoritative revision and effect outcomes. An `attempting` or
`outcome_unknown` operation may have been accepted. Request reconciliation and
retain all resource holds. The simulator seals either acceptance or absence while
serializing against late workers. A returned command receipt says that the request
was recorded, not that the workflow has already reached its next safe point.

Pause or emergency stop prevents new grant redemption at subsequent boundaries.
Cancellation records intent and observes already accepted effects; it never undoes
an effect or releases allocations. Emergency holds create durable alert deliveries.
The configured receiver must durably acknowledge the same event ID and return a
receipt ID before Lifecycle marks delivery complete. Inspect the receipt and
attributable operator command; a configured URL is not proof of delivery.

Resume only after the displayed independent observation, current authority and
recovery boundary permit it. `retry_unstarted` requires sealed absence and cannot
cross a target-first-write boundary. After possible target writes, keep the source
fenced and obtain separately approved forward recovery or reconciled source return.
P06 has no generic release, forced success, old-source restart or blind retry API.

When evidence is pending, restore the Assurance dependency and verify its digest,
source and independent observation checks. Committed-fact custody may finish after
executor revocation, but new effects and user retrieval still require current
permissions. Evidence review remains E2 and cannot publish native support.

## Restore and upgrade

Use [control-plane restore](restore-control-plane.md) and preserve the independently
held epoch. Stop effect ingress before restore, rotate the external epoch, restore
Lifecycle/Temporal/evidence with an explicit version set, and start observation-only.
Compare stable workflow, operation and attempt IDs with the separate effect owner;
retain all unknown or missing journal holds. Do not restore an old external epoch,
reuse an old grant, discard accepted effects or copy an evidence count into a
completion decision. P06 intentionally provides no automatic epoch rebind. The
re-enable decision remains denied until independent reconciliation and newly bound
authority have an approved implementation for the affected scope.

Retain V1 workflow code and `p06-simulation-v1` routing until all V1 histories drain.
Run replay against retained histories before a worker update. Incompatible changes
use a new workflow type/queue and separately qualified migration strategy; changing
an in-flight effect graph or source artifact is not a routine replay upgrade.

## Verify and retain

Run `python scripts/p06/qualify.py --output <new-directory>` in the pinned toolchain
with `P05_POSTGRES_BIN` pointing to PostgreSQL 16 tools. The complete disposable
GitHub Actions campaign is `.github/workflows/p06-execution.yml`; its live driver
requires the explicit fixture environment and rejects ordinary deployments.
Retain source bindings, failed runs, all four journey observations, engine replay,
alert acknowledgements, evidence denials, restore decisions and browser results.
A skipped local PostgreSQL test supplies no database qualification.
