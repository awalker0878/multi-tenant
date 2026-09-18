# ADR-0015 — Build under deny and verify before and after activation

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-13`<br>
**Source chapters:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A successful create response does not establish effective policy, service dependencies or accepted operating readiness.

## Decision recorded in the source

Create infrastructure with mandatory controls effective before endpoint connection. Verify permitted and forbidden paths internally, satisfy required initial readiness, then enable only approved exposure and verify the live path.

## Alternatives and limits recorded in the source

Restricted non-production qualification can generate acceptance evidence before production is offered. It must not be relabelled production-ready merely because resources exist.

## Consequences

Activation has its own reversible boundary. Failed external checks withdraw exposure without destroying owned data. Required bootstrap flows must be narrow and attributable rather than an unrestricted temporary allow.

## Engineering and implementation obligations

Record stage completion, actual realization, independent path controls, protection ownership, initial readiness and the accepted production connection change.

## Requirement and code traceability

[AUTO-002](../assurance/requirements.md#AUTO-002) · [ONB-001](../assurance/requirements.md#ONB-001) · [ACPT-001](../assurance/requirements.md#ACPT-001) · [EXP-001](../assurance/requirements.md#EXP-001)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [docs/COMMISSIONING.md](../COMMISSIONING.md)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

No source module or conversion supplies production authorization or release of quarantine.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
