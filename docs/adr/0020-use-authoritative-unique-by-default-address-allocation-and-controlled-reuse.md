# ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Independent address writers and early reuse create conflicting ownership, stale DNS and ambiguous security attribution.

## Decision recorded in the source

Allocate tenant addresses uniquely by default through an authoritative delegated scope. Reserve before dependent creation, reconcile native allocations and release only after route, DNS/DHCP and policy cleanup with the approved reuse controls.

## Alternatives and limits recorded in the source

Overlap is a declared migration or service exception with translation and unambiguous ownership, not the standard tenancy model.

## Consequences

Platform IPAM must either own its delegated pool or reconcile with the enterprise allocator. Documentation prefixes in worked examples never become actual reservations.

## Engineering and implementation obligations

Identify prefix and name authority, reservation lifetime, confirmation, stale-record cleanup, reverse records and reuse quarantine. Preserve ownership of retained service records.

## Requirement and code traceability

[IPAM-001](../assurance/requirements.md#IPAM-001) · [IPAM-002](../assurance/requirements.md#IPAM-002) · [IPAM-003](../assurance/requirements.md#IPAM-003) · [IPAM-004](../assurance/requirements.md#IPAM-004)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/input_review.py](../../tools/input_review.py)
- [tools/dns_change.py](../../tools/dns_change.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Authoritative IPAM allocation and native DNS propagation remain external integration work; DNS change code does not allocate addresses.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
