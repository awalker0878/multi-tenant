# ADR-0018 — Separate tenant administration, WSD lifecycle and domain realization

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

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

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules](../../terraform/modules)
- [tools/input_review.py](../../tools/input_review.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

The actual tenant identities, approved shared-domain ownership and lifecycle integration remain unassigned.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
