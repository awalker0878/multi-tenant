# Retained-state conversion design and rehearsal

This is the early B48 design for the retained contracts named in the B04
[interface retirement register](../implementation/automation/phase0-interface-retirement.md).
It provides a bounded private archive, historical projection and reconciliation
rehearsal. It does not import the production database, stop an old writer, create
a workflow or grant a lease. Actual conversion, owner handover, deletion and final
qualification remain open. A successful local rehearsal is not native evidence.

## Ownership and conversion boundary

Keep one owner for each responsibility:

| Retained fact | Existing owner and proposed live handover |
| --- | --- |
| Canonical `hosting.platform/v1` workload and its revision | `validate_record` and `EnterpriseRecordStore`; preserve identity/revision and append-only history. Do not reset a retained revision to 1 to fit `create`, or manufacture approval from a historical generation. |
| Native endpoint/scope/resource identity | `NativeBinding`, canonical workload bindings and the current native ownership table; reconcile independently observed IDs before assigning an owner. |
| Started Terraform operation or delivery step | Retained ledger/journal owners and `NativeOperationRegistry`; preserve an uncertain start as unknown. Native absence, timeout or an expired lease does not authorize a retry. |
| Worker ownership and new epoch | Current worker/grant and native registry recovery owners; independently fence the old credentials, worker and accepted/queued requests before advancing an epoch. |
| Original bundle, approvals, source, outputs and credentials | Private restricted archive and the existing controlled backup/evidence custody process. Do not upload raw credential-bearing bundle files into a sanitized evidence API. |
| New service's initial mode | Observation only; no accepted legacy plan, generation, approval or conversion report grants mutation. Enable each scope through current authority after independent acceptance. |

A deployed importer needs a reviewed persistence migration recording the immutable
batch/source digests and per-record disposition under existing tenant RLS and
append-only audit ownership. Its transaction must bind canonical record history,
native identities, unresolved operations and the accepted ownership epoch together.
This rehearsal deliberately writes no alternative production record store or SQL
schema. That transaction and independent evidence authentication are future B48
implementation gates.

## Supported rehearsal inputs

The package-owned command is:

```sh
python -m provisioner.controlplane.conversion.rehearsal \
  --manifest /private/conversion/batch-manifest.json \
  --source-root /private/conversion/source-snapshot \
  --destination /private/conversion/rehearsals \
  --as-of 2026-10-03T20:00:00Z
```

Use the actual inventory capture/readback time. The `--as-of` value describes an
offline rehearsal, and cannot extend a credential, approval or native-contact
window. All paths must be owner-only POSIX files/directories without symlinks.
The source snapshot and destination must be separate. Keep the manifest outside
the source snapshot so the sealed file inventory does not include itself.

The first explicitly supported profile accepts one canonical current Workload
revision in one exact organization/tenant/WSD/workload/platform/endpoint/native
scope/location. It preserves complete `hosting-terraform-bundle/1` bundles,
their source/artifacts and `hosting-terraform-attempt/1` ledgers. Lifecycle/native
output projection is limited to OpenStack workload stacks and the current
`server_id`, `port_id`, `boot_volume_id`, `data_volume_ids` fields. A missing input
or output lifecycle stage is never implicitly `prepared`: the projection requires
all corresponding independent native observations to agree, otherwise it records
`UNRESOLVED` and holds. Originals are never rewritten.

Optional delivery journals use the actual `hosting-execution-event/1` reader and
the `hosting-delivery/2` replay owner to verify sequence, scope, predecessor
digests and completed-artifact bindings. Replay invokes no dispatcher. An
uncompleted step stays uncertain, and an unclosed delivery remains held.

Other retained profiles, arbitrary schema versions, reservations, IPAM/DNS,
backup objects, source/target packets and multiple workload revisions have no
implicit conversion. Inventory them before cutover and implement their own
explicit owner mappings. Unsupported/unrecognized files hold the scope. An
absent native inventory cannot be interpreted as zero native resources.

## Manifest contract

`hosting-retained-state-rehearsal/1` requires exactly these fields:

| Field | Meaning |
| --- | --- |
| `format`, `batchId`, `capturedAt` | Exact version, stable one-time batch ID and UTC source snapshot time. A reused batch ID cannot replace bytes. |
| `scope` | Exact `organizationId`, `tenantId`, `securityDomainId`, `workloadId`, `endpointId`, `nativeScopeId`, `locationId`, `platformFamily`, `environmentKey`, `siteKey`. |
| `sourceFileSha256` | Complete map of every relative regular file in the source snapshot to its raw-byte SHA-256, including bundle source, logs, secrets, ledgers and readback evidence. The tool rejects omitted, extra, changed, linked or oversized files. |
| `workloadFiles` | Relative paths of the canonical current Workload records; this bounded profile supports exactly one current revision. |
| `terraformRuns` | Relative bundle directories containing the original source and artifact closure. |
| `terraformLedgers` | Relative scope directories containing exact hashed `*.started.json`, `*.result.json`, `head.json` and optional `writer.lock`. |
| `deliveryJournals` | Relative delivery scope directories, including their original event/artifact closure; explicitly empty when independently inventoried absent. |
| `sourceCounts` | Independently counted `files`, `workloads`, `terraformRuns`, `terraformStarts`, `terraformResults`, `deliveryEvents`. Any source/observed count difference holds the report. |
| `evidence` | Exactly `nativeInventory`, `oldWriterFreeze`, `newOwnerSnapshot`, each a relative evidence path or explicit `null`. A null produces a hold. |

Limits are 10,000 files, 8 MiB per file and 64 MiB per batch. Large native state,
history or backup archives need a separately reviewed bounded profile; they are
not silently dropped to fit the limits. Ambiguous JSON and unknown fields/schema
versions are rejected. The console emits fixed hold codes/counts, never original
records, private paths or credential values.

## Reconciliation readbacks

These are controlled offline input documents whose bytes are sealed in the
inventory. The rehearsal checks shape, scope, identity and chronology; it does
not authenticate their signer/custodian. The report always retains
`evidenceAuthenticated: false`. Real acceptance requires independent custody,
signature and freshness verification through the actual authority/evidence owners.

| Format | Exact fields besides `format` and the complete `scope` |
| --- | --- |
| `hosting-retained-native-inventory/1` | `capturedAt`, `observerId`, `complete` boolean, `bindings` list. Each row has canonical `binding` and `lifecycleStage` (`prepared`, `bootstrap` or explicit null). Capture must be at/after the source snapshot; duplicate or foreign IDs reject, incomplete or missing IDs hold. |
| `hosting-retained-writer-freeze/1` | `frozenAt`, `observerId`, nonempty `oldWriters`. Each row has unique `writerId`, `frozen` boolean, positive `epoch`, and exact `proofDigest`. Freeze must precede/meet the source snapshot. Any unfrozen writer holds. The tool performs no shutdown or fencing. |
| `hosting-retained-owner-snapshot/1` | `capturedAt`, `observerId`, `observationOnly: true`, `owners`. Each row has canonical `binding`, positive `epoch` and `workerId: null`. IDs must match retained/native inventories; epochs must exceed every declared old-writer epoch. An active writer rejects the rehearsal. |

This conservative epoch comparison accepts one coherent old owner boundary per
scope. If deployed resources have independently advancing epochs, inventory and
review that ownership structure before extending the profile. Never lower an old
epoch or omit a writer merely to make the rehearsal pass.

## Operator sequence and acceptance

1. Enumerate actual deployed consumers and complete retained records per scope.
   Record reservations, IPAM/DNS, backup snapshots, transfer datasets, source and
   target tasks, worker/grant identities and data-disposition obligations even
   where this bounded profile does not yet convert them. Obtain actual counts;
   an empty repository example is not a deployed inventory.
2. Independently stop submissions and fence every old writer, its credentials and
   delayed/queued platform requests. Record that evidence. Copy originals only
   after the freeze boundary and seal all source bytes and expected counts.
   Preserve the originals in controlled, backed-up immutable custody.
3. Collect independent native and database ownership readbacks after the snapshot.
   Investigate absent or extra IDs and accepted/in-flight tasks. Do not translate
   a missing `.result.json`, failed process or lease timeout into safe failure.
4. Run the rehearsal and review `reconciliation.json`, `projection.json` and
   `originals/` under the private destination's batch ID. `REHEARSAL_HELD` exits 2;
   malformed/digest/schema conflicts are `REHEARSAL_REJECTED` and exit 2. An
   internally consistent `REHEARSAL_RECONCILED_OBSERVATION_ONLY` exits 0 while all
   database import/write/retry authority flags remain false.
5. Re-run the exact manifest/time after an interruption to complete publication.
   Existing files are compared byte-for-byte, never overwritten. A final report
   appears only after originals and projections publish. A changed source,
   archive, manifest or reconciliation time conflicts; use a newly reviewed batch
   for changed evidence. File permissions/publication checks do not substitute
   for deployment-level WORM custody or independent backup.
6. Implement/rehearse the live import transaction with existing record/registry
   owners, authenticating evidence and maintaining source/import counts/digests.
   Preserve unresolved starts in canonical recovery and keep their scopes held.
   Start the deployed new service observation only and compare all ownership
   epochs, native IDs, database/evidence high-water marks and retained data.
7. Obtain scope-specific owner acceptance through current authority. Only then
   enable new writers, remove superseded runtime paths/readers in the same
   reviewed release, and rerun affected B47 campaigns on that final source.
   Complete B49 pilot acceptance and B50 release after those campaigns pass.

## Local validation

```sh
python -m unittest tests.provisioning.conversion.test_rehearsal
```

The fixtures invoke the real saved-plan/attempt record writers and canonical
validator with substituted platform processes. They cover positive original
records, exact replay/tampered archives, missing native inventories, unknown
starts, conflicting stages, unadvanced ownership, malformed canonical data,
mixed old/new ledger versions, mismatched outputs/scopes/counts, duplicate IDs,
unknown/late files and protected-path/JSON/console behavior. These results prove
local conversion semantics only. Actual retained-state conversion, PostgreSQL
transactional import, signer/custodian authentication, native reconciliation,
old-writer fencing, owner acceptance and qualification require deployed evidence.
