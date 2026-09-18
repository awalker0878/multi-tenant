# ADR-0015 — Build under deny and verify before and after activation

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-13`<br>
**Source chapters:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) · [PROV §4](../implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) · [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [docs/COMMISSIONING.md](../COMMISSIONING.md)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

No source module or conversion supplies production authorization or release of quarantine.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
