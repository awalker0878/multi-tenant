# ADR-0003 — Let the infrastructure architecture lead the tooling

**Status:** Proposed<br>
**Accountable role:** Architecture authority / Automation platform<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-01`<br>
**Source chapters:** [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md) · [SDP §6](../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

The material must describe sites, resources, trust transitions and ownership before specifying automation. Otherwise a custom control application becomes the de facto architecture.

## Decision

Keep the physical and logical infrastructure design authoritative. Terraform and existing delivery systems implement defined resource responsibilities; a new portal, routing compiler or controller is not a prerequisite.

## Alternatives and source limitations

The source permits existing delivery tools. It explicitly rejects making a custom-controller project a prerequisite, without forbidding an independently justified future interface.

## Consequences

Architecture reviews can be performed without reading an API schema. Implementation still has to supply authorization, reservation, ordered execution and evidence; those functions do not disappear when their software design is kept subordinate.

## Engineering and implementation obligations

Trace every automated operation to a component, authority boundary and lifecycle work package. Keep detailed API and validation internals outside the main architecture narrative.

## Requirement and code traceability

[ARCH-001](../assurance/requirements.md#ARCH-001) · [TF-003](../assurance/requirements.md#TF-003) · [API-003](../assurance/requirements.md#API-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules](../../terraform/modules)
- [terraform/roots](../../terraform/roots)
- [ansible](../../ansible)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual site architecture adoption and the selected delivery-tool responsibility model remain implementation decisions.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
