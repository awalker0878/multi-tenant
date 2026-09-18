# ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §4](../operations/recovery-transition/4-recover-the-service-in-dependency-order.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A lost response or stopped runner does not prove that a native task failed or stopped. Replaying or deleting can duplicate resources or destroy data already written.

## Decision recorded in the source

Retain stable operation/resource identities and scoped records. Discover current native configuration and progress, preserve quarantine, and choose an authorized data-safe converge or compensation path only after resolving uncertainty.

## Alternatives and limits recorded in the source

The source allows operator intervention for ambiguous outcomes. It does not require a particular saga engine or make an old Terraform state file into infrastructure rollback.

## Consequences

Native task completion, selected configuration agreement, aggregate realization and effective packet-path evidence remain different observations. Compensations must preserve shared and held resources.

## Engineering and implementation obligations

Record actual writer exclusion, task identity, current generations, reservations, active containment and retained data before proposing further mutations.

## Requirement and code traceability

[AUTO-002](../assurance/requirements.md#AUTO-002) · [AUTO-003](../assurance/requirements.md#AUTO-003) · [STATE-003](../assurance/requirements.md#STATE-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/dns_change.py](../../tools/dns_change.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

True native fencing, automatic repair and actual approval authentication remain unimplemented; the reviewer never authorizes apply, delete or activation.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
