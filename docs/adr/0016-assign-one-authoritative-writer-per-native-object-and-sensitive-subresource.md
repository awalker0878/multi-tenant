# ADR-0016 — Assign one authoritative writer per native object and sensitive subresource

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-14`, `RD14-05`<br>
**Source chapters:** [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [WD §10](../solutions/internal-protected-workload/10-resource-ownership-protection-and-change-receipts.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Two tools managing the same native object can undo security controls or cause destructive replacement. Adopting an existing object is not authority to reconstruct it.

## Decision recorded in the source

Assign one accountable tool/controller to each object and sensitive subresource. Reconcile actual configuration and remove competing writers before a reviewed ownership transfer or import.

## Alternatives and limits recorded in the source

Keep an object under its existing native controller when a safe ownership handover is not established. Import is a distinct controlled lifecycle operation, not proof of compliance.

## Consequences

A resource shared by several WSDs must survive retirement of one consumer. Per-route and aggregate-route writers must not compete for the same router configuration.

## Engineering and implementation obligations

Supply the ownership schedule, expected immutable identities, non-destructive adoption plan, data-retention scope and actual writer-fencing evidence for interrupted work.

## Requirement and code traceability

[STATE-003](../assurance/requirements.md#STATE-003) · [TEN-003](../assurance/requirements.md#TEN-003) · [LIFE-002](../assurance/requirements.md#LIFE-002)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [tools/route_record_review.py](../../tools/route_record_review.py)
- [terraform/roots](../../terraform/roots)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual native writer exclusion and transfer acceptance remain external controls; an offline record checker does not implement fencing.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
