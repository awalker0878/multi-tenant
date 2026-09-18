# ADR-0033 — Separate live-service retirement from retained-data disposal

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md) · [SVC §4](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [PROV §6](../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md) · [OPS §6](../operations/recovery-transition/6-migrate-and-fail-back-without-conflicting-writers.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/dns_change.py](../../tools/dns_change.py)
- [tools/recovery_review.py](../../tools/recovery_review.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual retention decisions, media methods and verified native cleanup remain data-owner and service-owner work.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
