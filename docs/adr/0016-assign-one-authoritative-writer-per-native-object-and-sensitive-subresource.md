# ADR-0016 — Assign one authoritative writer per native object and sensitive subresource

**Status:** Proposed<br>
**Accountable role:** Automation platform / Service owner / Service management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-14`, `RD14-05`<br>
**Source chapters:** [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [WD §10](../solutions/internal-protected-workload/10-resource-ownership-protection-and-change-receipts.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.
> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.


## Context

Two tools managing the same native object can undo security controls or cause destructive replacement. Adopting an existing object is not authority to reconstruct it.

## Decision

Assign one accountable tool/controller to each object and sensitive subresource. Reconcile actual configuration and remove competing writers before a reviewed ownership transfer or import.

## Alternatives and source limitations

Keep an object under its existing native controller when a safe ownership handover is not established. Import is a distinct controlled lifecycle operation, not proof of compliance.

## Consequences

A resource shared by several WSDs must survive retirement of one consumer. Per-route and aggregate-route writers must not compete for the same router configuration.

A handoff records which writer owns each native object and which process can still finish after interruption. Recovery of state or runner does not itself fence a native operation; scoped completion and data-safe compensation need evidence.

## Engineering and implementation obligations

Supply the ownership schedule, expected immutable identities, non-destructive adoption plan, data-retention scope and actual writer-fencing evidence for interrupted work. Validate these dependencies and record their owner, accepted configuration and failure/recovery observations before the affected service is offered.

## Requirement and code traceability

[STATE-003](../assurance/requirements.md#STATE-003) · [TEN-003](../assurance/requirements.md#TEN-003) · [LIFE-002](../assurance/requirements.md#LIFE-002) · [STATE-002](../assurance/requirements.md#STATE-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [tools/route_record_review.py](../../tools/route_record_review.py)
- [terraform/roots](../../terraform/roots)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual native writer exclusion and transfer acceptance remain external controls; an offline record checker does not implement fencing.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
