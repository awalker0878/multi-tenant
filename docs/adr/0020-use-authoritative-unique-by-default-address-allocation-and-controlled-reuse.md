# ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse

**Status:** Proposed<br>
**Accountable role:** Network engineering / Automation platform<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Independent address writers and early reuse create conflicting ownership, stale DNS and ambiguous security attribution.

## Decision

Allocate tenant addresses uniquely by default through an authoritative delegated scope. Reserve before dependent creation, reconcile native allocations and release only after route, DNS/DHCP and policy cleanup with the approved reuse controls.

## Alternatives and source limitations

Overlap is a declared migration or service exception with translation and unambiguous ownership, not the standard tenancy model.

## Consequences

Platform IPAM must either own its delegated pool or reconcile with the enterprise allocator. Documentation prefixes in worked examples never become actual reservations.

## Engineering and implementation obligations

Identify prefix and name authority, reservation lifetime, confirmation, stale-record cleanup, reverse records and reuse quarantine. Preserve ownership of retained service records.

## Requirement and code traceability

[IPAM-001](../assurance/requirements.md#IPAM-001) · [IPAM-002](../assurance/requirements.md#IPAM-002) · [IPAM-003](../assurance/requirements.md#IPAM-003) · [IPAM-004](../assurance/requirements.md#IPAM-004)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/input_review.py](../../tools/input_review.py)
- [tools/dns_change.py](../../tools/dns_change.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Authoritative IPAM allocation and native DNS propagation remain external integration work; DNS change code does not allocate addresses.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
