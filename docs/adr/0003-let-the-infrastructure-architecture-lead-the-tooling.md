# ADR-0003 — Let the infrastructure architecture lead the tooling

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-01`<br>
**Source chapters:** [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §2](../architecture/reference/2-design-drivers-and-selected-reference-pattern.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md) · [SDP §6](../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules](../../terraform/modules)
- [terraform/roots](../../terraform/roots)
- [ansible](../../ansible)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual site architecture adoption and the selected delivery-tool responsibility model remain implementation decisions.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
