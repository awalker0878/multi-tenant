# ADR-0034 — Classify change by architectural impact rather than file location

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [SDP §6](../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A tenant repository can target a shared gateway or platform, but its file location does not lower the authority or blast radius of that change.

## Decision recorded in the source

Separate routine consumption changes from security connectivity, shared foundation, profile/trust, emergency and retirement changes. Bind the relevant resource owners, review and recovery requirements to the actual effect.

## Alternatives and limits recorded in the source

Preauthorization can cover routine scale inside an accepted envelope. New zone sharing, exposure, inspection obligations, management authority or recovery promises require the corresponding architecture/security decision.

## Consequences

A material change can invalidate inherited evidence or affect several consumers. Unsupported rollback can require forward repair or restore rather than an assumed software downgrade.

## Engineering and implementation obligations

Trace affected interfaces, service parameters, dependencies, current state, supported versions and operating conditions; update the accepted design and as-built records deliberately.

## Requirement and code traceability

[CICD-001](../assurance/requirements.md#CICD-001) · [CICD-002](../assurance/requirements.md#CICD-002) · [VULN-001](../assurance/requirements.md#VULN-001) · [VULN-002](../assurance/requirements.md#VULN-002) · [OPS-001](../assurance/requirements.md#OPS-001)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/plan_review.py](../../tools/plan_review.py)
- [.github/workflows/validate.yml](../../.github/workflows/validate.yml)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual change classification, approval authority, installed support status and operational ownership are not supplied by CI success.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
