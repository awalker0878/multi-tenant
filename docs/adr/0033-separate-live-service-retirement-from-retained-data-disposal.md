# ADR-0033 — Separate live-service retirement from retained-data disposal

**Status:** Proposed<br>
**Accountable role:** Service management / Data owner / Storage operations<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [OPS §6](../operations/recovery-transition/6-migrate-and-fail-back-without-conflicting-writers.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A resource destroy can remove the paths and keys needed to meet retention obligations, or delete a shared object still required by another service.

## Decision

Retire live access through a dependency-aware workflow. Preserve required exports, holds, copies and keys; remove obsolete routes, DNS and authority; sanitize only data approved for reuse or disposal.

## Alternatives and source limitations

Held data remains in a separately accountable retention scope. It is not labelled destroyed merely because the live VM or volume record was removed.

## Consequences

Address, name and storage reuse must not inherit stale permissions. A shared key cannot be destroyed as though it were exclusive to one retiring workload.

## Engineering and implementation obligations

Maintain copy lineage, remaining obligations, disposal method/evidence, key dependency, final access revocation and a retained service identity/tombstone.

## Requirement and code traceability

[LIFE-001](../assurance/requirements.md#LIFE-001) · [LIFE-002](../assurance/requirements.md#LIFE-002) · [LIFE-003](../assurance/requirements.md#LIFE-003) · [STO-003](../assurance/requirements.md#STO-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/dns_change.py](../../tools/dns_change.py)
- [tools/recovery_review.py](../../tools/recovery_review.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual retention decisions, media methods and verified native cleanup remain data-owner and service-owner work.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
