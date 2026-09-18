# ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `RD14-03`<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) · [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [PBS §7](../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Tenant-editable selectors, additive security groups, port-security changes or extra attachments can widen the effective policy even when a baseline rule exists.

## Decision recorded in the source

Keep provider mutation authority over the mandatory network/policy/attachment envelope for the base service. Permit declared self-service through accepted workflows rather than unrestricted native edits.

## Alternatives and limits recorded in the source

Direct delegation is a separately qualified service extension whose permissions cannot expand the mandatory envelope. An additive allow mechanism must not be described as a deny hierarchy.

## Consequences

Administrative tenancy and effective network enforcement are separate. Same-host and same-subnet traffic needs enforcement even when no physical edge is traversed.

## Engineering and implementation obligations

Test selector changes, default rules, additional groups, address pairs, NICs and external-network permissions. Prove policy persists through relocation and supported lifecycle changes.

## Requirement and code traceability

[MICRO-001](../assurance/requirements.md#MICRO-001) · [MICRO-002](../assurance/requirements.md#MICRO-002) · [MICRO-003](../assurance/requirements.md#MICRO-003) · [OS-001](../assurance/requirements.md#OS-001) · [OS-002](../assurance/requirements.md#OS-002) · [NSX-001](../assurance/requirements.md#NSX-001) · [NUT-003](../assurance/requirements.md#NUT-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Native RBAC/API policy and the real immutable baseline need platform qualification; the source modules do not prove that tenant operators cannot bypass them.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
