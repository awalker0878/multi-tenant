# ADR-0020 — Use authoritative unique-by-default address allocation and controlled reuse

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [NET §4](../engineering/fabric/4-address-naming-and-protocol-family-decisions.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/input_review.py](../../tools/input_review.py)
- [tools/dns_change.py](../../tools/dns_change.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Authoritative IPAM allocation and native DNS propagation remain external integration work; DNS change code does not allocate addresses.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
