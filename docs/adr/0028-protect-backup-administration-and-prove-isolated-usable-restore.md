# ADR-0028 — Protect backup administration and prove isolated usable restore

**Status:** Proposed<br>
**Accountable role:** Backup operations / Continuity management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [OPS §3](../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Successful capture does not establish useful recovery. A compromised production identity should not gain authority to delete the copies intended to survive it.

## Decision

Separate capture orchestration, data movement and backup administration. Protect the required independent copies, catalogue, configuration and keys, and verify restore in an isolated eligible recovery domain before reconnection.

## Alternatives and source limitations

Capture may use supported snapshot/API/proxy or guest-agent paths. The actual method follows service consistency and platform support, not a universally assumed data flow.

## Consequences

Retained copies can outlive the live WSD and require continuing key and access custody. Recovery acceptance includes usable data and dependency restoration, not just a completed VM restore.

## Engineering and implementation obligations

Assign capture, deletion, hold, restore and data-validation authorities; prove production credentials cannot alter protected retention; measure the recovered consistency point and service time.

## Requirement and code traceability

[BKP-001](../assurance/requirements.md#BKP-001) · [BKP-002](../assurance/requirements.md#BKP-002) · [BKP-003](../assurance/requirements.md#BKP-003) · [BKP-004](../assurance/requirements.md#BKP-004) · [REC-001](../assurance/requirements.md#REC-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [docs/IMPLEMENTATION_SCOPE.md](../IMPLEMENTATION_SCOPE.md)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

No production backup product, catalogue recovery or KMS integration is implemented by this documentation release.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
