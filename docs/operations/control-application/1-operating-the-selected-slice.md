# Operating the selected control-application slice

This increment installs backup/observation-only restore, scoped health and
restricted incident-intake owners. It provides minimum operating admission for
the selected VMware to OpenStack Ubuntu 24.04 application route. It adds no
deployed HA, site restore acceptance, native campaign success or production grant.

## Current owners and deployment

| Requirement | Installed owner | Required site input |
|---|---|---|
| Consistent control database archive | `provisioner.controlplane.operations.recovery` | Separate NOSUPERUSER, read-only BYPASSRLS backup custodian; PostgreSQL clients matching the deployed server |
| Observation-only isolated restore | Same owner | Empty `hosting_observation_restore_*` database, NOSUPERUSER/NOBYPASSRLS owner, CONNECT revoked from other identities, independently retained manifest digest |
| Stuck/held jobs, unknown native work, containment, stale discovery and evidence availability | `provisioner.controlplane.operations.health` | Tenant-scoped NOSUPERUSER/NOBYPASSRLS SELECT role, actual independent evidence verifier |
| Incident delivery and acknowledgement | `IncidentDispatcher` and `retain_delivery` | Verified dedicated HTTPS ITSM intake, private token, exact idempotency/digest receipt and independent evidence signer |
| Minimum operating admission | `OperationsActionGate` | Actual signed B44–B46 prerequisite acceptance retained through the existing evidence repository |
| Native action qualification plus minimum operating admission | `operations.runtime.build_action_gate` | Current dossier/provenance/campaign/target/capacity indexes and distinct operating-signer Vault trust |

The monitor, backup and their timer units are under `deploy/operations/`. Install
the distribution into `/opt/hosting`, commission dedicated `hosting-ops` and
`hosting-backup` identities, and populate protected environment files outside
the repository. Each monitor instance selects one organization/tenant. Unit
examples use `/var/lib/hosting-control-backup` for fresh archives and require
the site to configure independent protected replication/retention. A local
archive directory does not provide WORM retention or disaster recovery.

The monitor's `HOSTING_OPS_DSN` is a separate SELECT identity. Independent
evidence configuration uses the existing `HOSTING_EVIDENCE_*` settings and its
own `HOSTING_RUNTIME_DSN`; dispatch additionally requires the independently
controlled checkpoint signing credential. `HOSTING_OPS_INCIDENT_ENDPOINT`,
`HOSTING_OPS_INCIDENT_CA`, and `HOSTING_OPS_INCIDENT_TOKEN_FILE` select the ITSM
intake. It must accept an `Idempotency-Key` and return `signalId`,
`signalSha256`, `incidentId`, `acknowledgedBy`, and `acknowledgedAt`. Delivery
without an actual operator identity/time remains unacknowledged. Each receipt
is retained in the existing evidence stream and independently checkpointed.
The service's health-held exit code is expected; a failed receipt retention
remains held and the intake's idempotency contract allows safe delivery retry.

`HOSTING_OPS_ACCEPTANCE_VAULT_TRUST_JSON` contains the operating signer's
reviewed Vault key aliases/path pairs. Neither aliases nor actual key paths may
overlap evidence checkpoint keys. The configured verify-only identity must
have verify permission for those keys. Current qualification paths may be
selected through `HOSTING_QUALIFICATION_INDEX`,
`HOSTING_VERSION_PROVENANCE_INDEX`, `HOSTING_QUALIFICATION_CAMPAIGN_INDEX`,
`HOSTING_TARGET_SELECTION_INDEX`, and `HOSTING_CAPACITY_INDEX`. Every effect
rereads the protected files; packaged empty indexes keep native actions held.

## Minimum operating acceptance before native writes

An operating reviewer first executes and retains actual evidence for control
database observation restore, independent evidence high-water reconciliation,
Temporal accepted-job recovery, old-writer epoch fencing, HA stop/upgrade
containment, delivered/operator-acknowledged alerts, least-privilege negatives,
transfer-worker isolation and signed artifact provenance. These are selected
slice prerequisites; full final migration qualification and pilot acceptance
remain separate.

The reviewer signs a `hosting-selected-operating-acceptance/1` payload with
the exact `scopeDigest(selection)`, code revision, plan ID, revocation epoch,
acceptance/review instants and all nine `MINIMUM_PREREQUISITES` receipts.
Every receipt has an accepted result, retained evidence reference/SHA-256,
independent observer reference and observation/freshness instants. The
dedicated operating signer creates the existing `payload`/`keyId`/base64
`signature` envelope. Retain that original envelope with
`EvidenceRepository.append`, kind `VERIFICATION_RESULT`, event key
`acceptance_event_key(acceptance_digest(envelope))` and subject ID
`scope_digest(selection)`. Bind the envelope digest as
`selection.operationsAcceptanceDigest` before reviewing the canonical plan.
This storage action does not grant approval; signature, current evidence,
exact plan epoch and runtime holds are verified again before each native write.

The minimum gate requires a current STARTED/RUNNING admitted job and refuses
new writes while a tenant has IN_FLIGHT, TASK_ACCEPTED or UNCERTAIN native work
or active containment. Resolve accepted work through the existing independently
observed reconciliation path. The gate cannot expire a native operation,
release an ownership epoch, unhold a job or delete a source.

An accepted original operation has a separate typed continuation path. It
revalidates the actual current B10 `WorkerGrant`/authenticated worker and B11
lease in the same transaction, locks the exact original IN_FLIGHT/TASK_ACCEPTED
intent, and excludes only that one operation from the unresolved count.
UNCERTAIN, expired/changed grants, unrelated operations and containment remain
held. The ordinary preclaim admission path cannot be reused as a continuation
or bypassed by a caller flag.
The named local observation path verifies original signed scope/custody and
retained job/plan bindings while allowing held/terminal status, revocation and
unknown/contained operations to remain visible. The caller must independently
authorize the reader. That path issues no native identity/credential or write
authority and cannot be supplied to an effect runner.

## Backup and observation restore

Run `python -m provisioner.controlplane.operations.recovery backup --directory
<new-private-archive-directory>` with a protected `HOSTING_BACKUP_DSN` using
verify-full TLS. The owner exports one consistent PostgreSQL snapshot and
passes it to `pg_dump`, retaining every table's count/digest, migration ledger,
sequence and RLS state. Epochs, accepted intents and evidence high-water rows
are included in those digests. The backup custodian must independently retain
the exact `manifest.json` digest and archive digest with the archive.
Table digests use UTC/ISO values and deterministic byte collation. Sequences
are nontransactional PostgreSQL state; if their values change during the dump,
the owner refuses to publish a success manifest. Drain the relevant control
writers through the existing operating authority and retry that archive.

Commission a disconnected empty observation database whose name starts
`hosting_observation_restore_`, revoke CONNECT from identities other than its
restore owner, and set `HOSTING_RESTORE_DSN` plus independently obtained
`HOSTING_RESTORE_MANIFEST_SHA256`. Run the same module's `restore` mode with
the archived directory. The owner rejects changed manifest/archive bytes,
restores without runtime ACLs, reapplies deny-first PUBLIC privileges and RLS,
compares retained rows/sequences/migrations and sets the database default to
read-only. An equal archive remains observation-only. Reconcile independent
Object Lock/Vault checkpoints, Temporal histories/build routing, Terraform
state/backend versions, native owner epochs and old writer fencing before
requesting separate current operating and activation acceptance. Restoring
database rows alone never authorizes native writes.

Temporal persistence backups, workflow retention, independent Object Lock
replication, Vault recovery custody and Terraform backend replication remain
site-owned external operating inputs. These controls are explicit holds in
the restore report. No deployment or end-to-end restore campaign was run here.

## Stuck or held job

Inspect the exact immutable job/plan revision and its last retained event.
Identify the authority, input, resource or recovery hold before proposing a
reviewed resumption. A timeout does not prove a native operation failed and
does not authorize starting it again. WAITING_APPROVAL is an expected state;
the monitor does not label it stuck merely because time passed.

## Uncertain native effect

Keep writers contained. Inspect the existing operation intent, grant, task ID,
resource identity and independent native observations. Reconcile through the
existing native registry's reviewed recovery path. Never use task disappearance,
lease expiry, a successful Terraform exit or a monitor alert as proof of no effect.

## Active containment

Route the retained incident to the incident authority and keep worker/endpoint
holds in place. A successful data check, fresh qualification packet or alert
acknowledgement cannot clear native containment.

## Evidence or recovery hold

Investigate the independent checkpoint service, retained blobs, Vault key trust
and signed high-water marks using verify-only custody. Do not reinitialize a
stream over a restored database or replace a newer independent checkpoint with
an older archive. Restore remains read-only until reconciliation and new
operating acceptance; the runtime has no degraded writable fallback.

## Stale discovery

Inspect the environment's latest retained freshness check and authorized
collection budget. Schedule an actual bounded collection through the discovery
owner and independently verify visibility. A missing/stale check does not grant
platform contact or permit carrying old comparison results into execution.

## Verification boundaries

`python -m unittest discover -s tests/provisioning/operations -v` exercises
signed synthetic current/expired/revoked/scope/action/restore holds and actual
loopback TLS incident delivery. Process/DB doubles remain synthetic. If the
installed qemu-img/bwrap pair or kernel namespaces are unavailable, image
conversion is held with no unconfined fallback. PostgreSQL engine/archive,
deployed HA/DR, site alerts and independent native campaigns require their
actual approved environments.
