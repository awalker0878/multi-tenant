# ADR-0016 — Assign one authoritative writer per native object and sensitive subresource

**Status:** Proposed<br>
**Accountable role:** Native configuration owner and change authority<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-14`, `RD14-05`<br>
**Source chapters:** [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [WD §10](../solutions/internal-protected-workload/10-resource-ownership-protection-and-change-receipts.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [tools/route_record_review.py](../../tools/route_record_review.py)
- [terraform/roots](../../terraform/roots)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual native writer exclusion and transfer acceptance remain external controls; an offline record checker does not implement fencing.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
