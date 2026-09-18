# ADR-0018 — Separate tenant administration, WSD lifecycle and domain realization

**Status:** Proposed<br>
**Accountable role:** Architecture authority / Automation platform / Service owner<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [VND §1](../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

One tenant can own several services and security domains. Treating the tenant, zone, routing context and deployment lifecycle as the same object causes ownership and deletion ambiguity.

## Decision

Use a tenant for administrative entitlement; a WSD for a bounded hosting environment; a logical Security Domain for zone class and authority; and an instance for the site/platform realization. Give each network one instance owner.

## Alternatives and source limitations

A shared domain is permitted only with an approved sharing policy and independent lifecycle owner. The source does not make a WSD synonymous with one Terraform state or one custom API object.

## Consequences

Identical zone labels across tenants grant no connectivity. A domain can outlive a WSD and be recreated on another platform without changing its security purpose.

## Engineering and implementation obligations

Carry stable ownership through network/resource attachment, shared dependencies, migration and retirement. Prevent an extra NIC or a tenant-controlled label from changing authority.

## Requirement and code traceability

[INV-001](../assurance/requirements.md#INV-001) · [TEN-001](../assurance/requirements.md#TEN-001) · [WSD-001](../assurance/requirements.md#WSD-001) · [SDI-001](../assurance/requirements.md#SDI-001) · [MODEL-001](../assurance/requirements.md#MODEL-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules](../../terraform/modules)
- [tools/input_review.py](../../tools/input_review.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

The actual tenant identities, approved shared-domain ownership and lifecycle integration remain unassigned.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
