# ADR-0033 — Separate live-service retirement from retained-data disposal

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [OPS §6](../operations/recovery-transition/6-migrate-and-fail-back-without-conflicting-writers.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A resource destroy can remove the paths and keys needed to meet retention obligations, or delete a shared object still required by another service.

## Decision recorded in the source

Retire live access through a dependency-aware workflow. Preserve required exports, holds, copies and keys; remove obsolete routes, DNS and authority; sanitize only data approved for reuse or disposal.

## Alternatives and limits recorded in the source

Held data remains in a separately accountable retention scope. It is not labelled destroyed merely because the live VM or volume record was removed.

## Consequences

Address, name and storage reuse must not inherit stale permissions. A shared key cannot be destroyed as though it were exclusive to one retiring workload.

## Engineering and implementation obligations

Maintain copy lineage, remaining obligations, disposal method/evidence, key dependency, final access revocation and a retained service identity/tombstone.

## Requirement and code traceability

[LIFE-001](../assurance/requirements.md#LIFE-001) · [LIFE-002](../assurance/requirements.md#LIFE-002) · [LIFE-003](../assurance/requirements.md#LIFE-003) · [STO-003](../assurance/requirements.md#STO-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/dns_change.py](../../tools/dns_change.py)
- [tools/recovery_review.py](../../tools/recovery_review.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual retention decisions, media methods and verified native cleanup remain data-owner and service-owner work.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
