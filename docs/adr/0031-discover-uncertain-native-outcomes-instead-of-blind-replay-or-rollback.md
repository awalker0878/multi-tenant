# ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback

**Status:** Proposed<br>
**Accountable role:** Automation platform<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §4](../operations/recovery-transition/4-recover-the-service-in-dependency-order.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A lost response or stopped runner does not prove that a native task failed or stopped. Replaying or deleting can duplicate resources or destroy data already written.

## Decision

Retain stable operation/resource identities and scoped records. Discover current native configuration and progress, preserve quarantine, and choose an authorized data-safe converge or compensation path only after resolving uncertainty.

## Alternatives and source limitations

The source allows operator intervention for ambiguous outcomes. It does not require a particular saga engine or make an old Terraform state file into infrastructure rollback.

## Consequences

Native task completion, selected configuration agreement, aggregate realization and effective packet-path evidence remain different observations. Compensations must preserve shared and held resources.

## Engineering and implementation obligations

Record actual writer exclusion, task identity, current generations, reservations, active containment and retained data before proposing further mutations.

## Requirement and code traceability

[AUTO-002](../assurance/requirements.md#AUTO-002) · [AUTO-003](../assurance/requirements.md#AUTO-003) · [STATE-003](../assurance/requirements.md#STATE-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/dns_change.py](../../tools/dns_change.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

True native fencing, automatic repair and actual approval authentication remain unimplemented; the reviewer never authorizes apply, delete or activation.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
