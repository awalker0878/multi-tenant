# ADR-0034 — Classify change by architectural impact rather than file location

**Status:** Proposed<br>
**Accountable role:** Change authority / Automation platform / Vulnerability management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [SDP §6](../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A tenant repository can target a shared gateway or platform, but its file location does not lower the authority or blast radius of that change.

## Decision

Separate routine consumption changes from security connectivity, shared foundation, profile/trust, emergency and retirement changes. Bind the relevant resource owners, review and recovery requirements to the actual effect.

## Alternatives and source limitations

Preauthorization can cover routine scale inside an accepted envelope. New zone sharing, exposure, inspection obligations, management authority or recovery promises require the corresponding architecture/security decision.

## Consequences

A material change can invalidate inherited evidence or affect several consumers. Unsupported rollback can require forward repair or restore rather than an assumed software downgrade.

## Engineering and implementation obligations

Trace affected interfaces, service parameters, dependencies, current state, supported versions and operating conditions; update the accepted design and as-built records deliberately.

## Requirement and code traceability

[CICD-001](../assurance/requirements.md#CICD-001) · [CICD-002](../assurance/requirements.md#CICD-002) · [VULN-001](../assurance/requirements.md#VULN-001) · [VULN-002](../assurance/requirements.md#VULN-002) · [OPS-001](../assurance/requirements.md#OPS-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/plan_review.py](../../tools/plan_review.py)
- [.github/workflows/validate.yml](../../.github/workflows/validate.yml)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual change classification, approval authority, installed support status and operational ownership are not supplied by CI success.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
