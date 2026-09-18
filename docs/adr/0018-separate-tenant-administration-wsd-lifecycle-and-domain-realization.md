# ADR-0018 — Separate tenant administration, WSD lifecycle and domain realization

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

One tenant can own several services and security domains. Treating the tenant, zone, routing context and deployment lifecycle as the same object causes ownership and deletion ambiguity.

## Decision recorded in the source

Use a tenant for administrative entitlement; a WSD for a bounded hosting environment; a logical Security Domain for zone class and authority; and an instance for the site/platform realization. Give each network one instance owner.

## Alternatives and limits recorded in the source

A shared domain is permitted only with an approved sharing policy and independent lifecycle owner. The source does not make a WSD synonymous with one Terraform state or one custom API object.

## Consequences

Identical zone labels across tenants grant no connectivity. A domain can outlive a WSD and be recreated on another platform without changing its security purpose.

## Engineering and implementation obligations

Carry stable ownership through network/resource attachment, shared dependencies, migration and retirement. Prevent an extra NIC or a tenant-controlled label from changing authority.

## Requirement and code traceability

[INV-001](../assurance/requirements.md#INV-001) · [TEN-001](../assurance/requirements.md#TEN-001) · [WSD-001](../assurance/requirements.md#WSD-001) · [SDI-001](../assurance/requirements.md#SDI-001) · [MODEL-001](../assurance/requirements.md#MODEL-001)

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules](../../terraform/modules)
- [tools/input_review.py](../../tools/input_review.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

The actual tenant identities, approved shared-domain ownership and lifecycle integration remain unassigned.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
