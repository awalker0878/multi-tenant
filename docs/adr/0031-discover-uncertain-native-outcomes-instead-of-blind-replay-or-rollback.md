# ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md) · [PROV §5](../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md) · [OPS §4](../operations/recovery-transition/4-recover-the-service-in-dependency-order.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/recovery_review.py](../../tools/recovery_review.py)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/dns_change.py](../../tools/dns_change.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

True native fencing, automatic repair and actual approval authentication remain unimplemented; the reviewer never authorizes apply, delete or activation.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
