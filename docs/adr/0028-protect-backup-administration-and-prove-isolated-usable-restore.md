# ADR-0028 — Protect backup administration and prove isolated usable restore

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [OPS §3](../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Successful capture does not establish useful recovery. A compromised production identity should not gain authority to delete the copies intended to survive it.

## Decision recorded in the source

Separate capture orchestration, data movement and backup administration. Protect the required independent copies, catalogue, configuration and keys, and verify restore in an isolated eligible recovery domain before reconnection.

## Alternatives and limits recorded in the source

Capture may use supported snapshot/API/proxy or guest-agent paths. The actual method follows service consistency and platform support, not a universally assumed data flow.

## Consequences

Retained copies can outlive the live WSD and require continuing key and access custody. Recovery acceptance includes usable data and dependency restoration, not just a completed VM restore.

## Engineering and implementation obligations

Assign capture, deletion, hold, restore and data-validation authorities; prove production credentials cannot alter protected retention; measure the recovered consistency point and service time.

## Requirement and code traceability

[BKP-001](../assurance/requirements.md#BKP-001) · [BKP-002](../assurance/requirements.md#BKP-002) · [BKP-003](../assurance/requirements.md#BKP-003) · [BKP-004](../assurance/requirements.md#BKP-004) · [REC-001](../assurance/requirements.md#REC-001)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [docs/IMPLEMENTATION_SCOPE.md](../IMPLEMENTATION_SCOPE.md)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

No production backup product, catalogue recovery or KMS integration is implemented by this documentation release.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
