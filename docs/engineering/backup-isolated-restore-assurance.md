# Backup protection and isolated-restore assurance

**Purpose:** make the recovery evidence required by BKP-001 through BKP-004 executable without turning this repository into a backup product, storage controller, KMS, catalogue or recovery orchestrator.

A successful backup task is not a recovery promise. The service is ready for its backup/recovery dependency only when the reviewed BackupPolicy is represented by current evidence for independent copy protection, retained catalogue/key access and a useful isolated restore at the accepted cadence.

## Source requirements

- BKP-001 keeps backup management interfaces separate from ordinary backup consumption.
- BKP-002 applies the same tenant, security-zone, identity and evidence controls to restore as to backup ingestion.
- BKP-003 requires a BackupPolicy covering consistency, retention, location, key and protected-copy requirements plus successful isolated restore at policy cadence.
- BKP-004 prevents production credentials from deleting/reducing independent protected copies or destroying the catalogue/keys needed for recovery.
- STO-001 retains copy ownership, access, key, placement/retention and lineage obligations.
- CRY-002 prevents key destruction from invalidating required retained-data recovery.
- REL-001 keeps actual RTO/RPO, dependencies and test cadence in approved service/recovery profiles rather than inferring them from an impact category.

## Evidence record

The active index is `sources/capabilities/backup_restore_assurance_index.json` and is intentionally empty today.

A future assurance record binds the WSD/request to an opaque BackupPolicy and service-class reference, exact consistency/retention/location/key/protected-copy/capture/data-path/restore-target/recovery profiles, accountable backup/data/recovery/key owners, and explicit exclusions.

### Independent protection

The record requires evidence that all four disallowed production/consumer powers are DENIED:

- backup consumer access to backup management;
- production deletion of the protected copy;
- production reduction of protected-copy retention;
- production destruction of the key required to recover the retained copy.

Each denial carries its own evidence reference and observation time. These are evidence claims, not credentials or ACL configuration stored in Git.

### Protected copy

The record carries opaque references for the copy, repository, catalogue and key dependency together with capture/retention times and integrity, catalogue access, key access and lineage evidence. No backup payload, key, catalogue content or native repository identifier is placed in this public evidence model.

### Isolated restore

CURRENT_ASSURED requires an isolated restore witness tied to the same protected copy. The witness records the approved test-set reference, isolated target reference, restore start, recovered consistency point, service/data-owner acceptance, evidence-valid-until date, consistency/isolation/useful-data/identity-key evidence and observed RTO/RPO values.

Observed RTO/RPO are evidence only. This checker does not invent or approve thresholds; comparison to service objectives belongs to the approved RTO/RPO profile.

The restored target must remain production-disconnected during the exercise. Reconnect is a separate authorized action after isolation and data acceptance.

## Cadence and states

Supported evidence states are CURRENT_ASSURED, RESTORE_DUE, RETIREMENT_PENDING and UNCERTAIN.

CURRENT_ASSURED requires both the policy review and isolated-restore evidence to be current and the protected copy to remain retained. RESTORE_DUE is used when the accepted review/restore-evidence cadence has expired. UNCERTAIN blocks reliance until actual copy/catalogue/key/restore state is reconciled.

RETIREMENT_PENDING preserves retained-copy obligations after the live WSD begins retirement; live-service deletion never implies the retained copy, catalogue or recovery key may be discarded.

## Readiness preflight

`scripts/check_backup_restore_readiness.py` compares a WSD's required BackupPolicy, service class and required recovery-profile subset against the current assurance record.

A successful result is `BACKUP_RESTORE_ASSURANCE_CURRENT_NO_OPERATION_AUTHORIZED`. It is only a readiness prerequisite. It does not authorize capture, deletion, key destruction, restore, restored-service reconnect, infrastructure apply or production activation.

Current repository state remains held because the active assurance index is empty:

```sh
python scripts/check_backup_restore_readiness.py examples/backup_restore_readiness_intent.json.example --as-of 2026-09-18T19:00:00Z --expected-status HOLD_NO_CURRENT_BACKUP_ASSURANCE
```

Actual backup/storage/KMS products, API versions, copy IDs, data, credentials, service endpoints and measured service objectives remain site/service-owner decisions and native qualification work.

[Backup capture and isolated restore architecture](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [Storage and backup architecture](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [Recovery/retirement implementation](../implementation/native-reference/recovery-retirement.md)
