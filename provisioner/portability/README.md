# Dataset delivery and verification

Mobility uses the existing delivery runner and the same native bootstrap graph as
ordinary provisioning. A dataset is one explicit transfer, not a shared success
flag. Each `backup-restore` dataset compiles to its own `dataset_restore` step.
Every declared consistency group joins its children through `dataset_acceptance`;
service acceptance and cutover depend on all group joins.

An operator binds a captured dataset to a reviewed transfer envelope using these
optional fields on a `WorkloadMobility.spec.data.datasets` item:

```yaml
transferManifest:
  datasetId: application-dataset
  targetRef: application-target
  consistencyGroupId: application-group
  sha256: <SHA-256 of tools.run_files.encoded(transfer_envelope)>
```

`sha256` here identifies the complete `hosting-restic-transfer/1` envelope. It is
separate from the dataset's existing source-state `sha256`. The envelope contains
the canonical `MigrationPlan` and `TransferManifest`, original source execution
scope, destination execution scope, source configuration digest, repository ID,
exact native restic snapshot ID, file-manifest digest, target member and isolated
restore root. Canonical inventory observation IDs remain distinct from the native
restic snapshot ID. No compiler generates capture evidence or approves a grant.

Missing transfer bindings remain explicit plan holds. Duplicate dataset names,
dataset IDs, target mappings and manifest digests are rejected. Unsupported
transfer methods cannot be executed as restic restores. The reviewed delivery
parameters pin each child's source scope, dataset, target, group and envelope
hash; the runner also verifies the destination against its own scope.

Cross-scope execution needs a runtime-created `TransferGuard` backed by the
existing authority service. The guard binds an independently stored transfer hash
and rechecks the live worker, exact plan, independent approvals and owner lease
before and after repository commands. Command deadlines use the earliest trusted
identity, role, approval, lease or grant expiry. An ordinary restore-authority
file and transfer envelope alone cannot enable a foreign-scope restore.

The original capture manifest and receipt retain their source scope. The ordinary
restore receipt also retains that provenance. A separate
`hosting-restic-transfer-receipt/1` binds destination scope and member, exact
dataset/target, native snapshot, source/restore receipts and verified bytes.
Group verification requires a distinct source capture and restore receipt for
every child, complete group membership, and one exact canonical plan and source
observation. Missing, duplicated, substituted or misdirected evidence holds the
group.

Planning, verified file bytes, application acceptance and native qualification
are separate states. A group join proves file bytes only; it does not certify a
consistent application, authorize a writer, qualify a migration route, or activate
production. Native intent, uncertain-outcome reconciliation, credential brokering
and independently qualified site mutation routes remain runtime prerequisites.
The current read-only site credential listener does not become a mutation listener
by supplying these files. Interrupted restores retain their private artifacts and
must not be replayed blindly.
