# ADR-0003 — Let the infrastructure architecture lead the tooling

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-01`<br>
**Source chapters:** [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md) · [SDP §6](../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

The material must describe sites, resources, trust transitions and ownership before specifying automation. Otherwise a custom control application becomes the de facto architecture.

## Decision recorded in the source

Keep the physical and logical infrastructure design authoritative. Terraform and existing delivery systems implement defined resource responsibilities; a new portal, routing compiler or controller is not a prerequisite.

## Alternatives and limits recorded in the source

The source permits existing delivery tools. It explicitly rejects making a custom-controller project a prerequisite, without forbidding an independently justified future interface.

## Consequences

Architecture reviews can be performed without reading an API schema. Implementation still has to supply authorization, reservation, ordered execution and evidence; those functions do not disappear when their software design is kept subordinate.

## Engineering and implementation obligations

Trace every automated operation to a component, authority boundary and lifecycle work package. Keep detailed API and validation internals outside the main architecture narrative.

## Requirement and code traceability

[ARCH-001](../assurance/requirements.md#ARCH-001) · [TF-003](../assurance/requirements.md#TF-003) · [API-003](../assurance/requirements.md#API-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules](../../terraform/modules)
- [terraform/roots](../../terraform/roots)
- [ansible](../../ansible)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual site architecture adoption and the selected delivery-tool responsibility model remain implementation decisions.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
