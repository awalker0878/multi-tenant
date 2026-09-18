# ADR-0034 — Classify change by architectural impact rather than file location

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [SDP §6](../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/plan_review.py](../../tools/plan_review.py)
- [.github/workflows/validate.yml](../../.github/workflows/validate.yml)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual change classification, approval authority, installed support status and operational ownership are not supplied by CI success.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
