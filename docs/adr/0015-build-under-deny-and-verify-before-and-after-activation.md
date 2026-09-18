# ADR-0015 — Build under deny and verify before and after activation

**Status:** Proposed<br>
**Accountable role:** Automation platform / Service management / Security authority<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-13`<br>
**Source chapters:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A successful create response does not establish effective policy, service dependencies or accepted operating readiness.

## Decision

Create infrastructure with mandatory controls effective before endpoint connection. Verify permitted and forbidden paths internally, satisfy required initial readiness, then enable only approved exposure and verify the live path.

## Alternatives and source limitations

Restricted non-production qualification can generate acceptance evidence before production is offered. It must not be relabelled production-ready merely because resources exist.

## Consequences

Activation has its own reversible boundary. Failed external checks withdraw exposure without destroying owned data. Required bootstrap flows must be narrow and attributable rather than an unrestricted temporary allow.

## Engineering and implementation obligations

Record stage completion, actual realization, independent path controls, protection ownership, initial readiness and the accepted production connection change.

## Requirement and code traceability

[AUTO-002](../assurance/requirements.md#AUTO-002) · [ONB-001](../assurance/requirements.md#ONB-001) · [ACPT-001](../assurance/requirements.md#ACPT-001) · [EXP-001](../assurance/requirements.md#EXP-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [docs/COMMISSIONING.md](../COMMISSIONING.md)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

No source module or conversion supplies production authorization or release of quarantine.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
