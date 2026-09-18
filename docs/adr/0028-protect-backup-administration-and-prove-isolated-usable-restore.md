# ADR-0028 — Protect backup administration and prove isolated usable restore

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md) · [SVC §5](../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md) · [OPS §3](../operations/recovery-transition/3-run-maintenance-and-recover-interrupted-changes.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [docs/IMPLEMENTATION_SCOPE.md](../IMPLEMENTATION_SCOPE.md)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

No production backup product, catalogue recovery or KMS integration is implemented by this documentation release.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
