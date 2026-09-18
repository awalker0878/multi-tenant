# ADR-0014 — Bootstrap management and trust before consuming native APIs

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-12`<br>
**Source chapters:** [RA §21](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PBS §1](../engineering/platform-build/1-choose-the-platform-boundary-and-configuration-owner.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

An empty site cannot already depend on the APIs, identity, DNS, key service and state backend that it is being asked to build.

## Decision recorded in the source

Use supported hardware/platform installers and lifecycle tools to establish restricted management, trust and native APIs. Let Terraform manage supported resource operations after those prerequisites exist.

## Alternatives and limits recorded in the source

Temporary external bootstrap dependencies are allowed with named owners and a controlled transfer to steady state. An unsupported shell action inside Terraform is not equivalent to a supported declarative resource.

## Consequences

Some installation tasks can proceed in parallel, but tenant allocation must not consume unaccepted security, storage or management foundations. Bootstrap cleanup must not erase the only usable recovery material.

## Engineering and implementation obligations

Document dependency cuts, temporary credentials, verified artifacts, native operation coverage and accepted handover; revoke temporary grants after successful transfer.

## Requirement and code traceability

[AUTO-001](../assurance/requirements.md#AUTO-001) · [MGT-005](../assurance/requirements.md#MGT-005) · [REC-001](../assurance/requirements.md#REC-001) · [QUAL-001](../assurance/requirements.md#QUAL-001)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/README.md](../../terraform/README.md)
- [docs/COMMISSIONING.md](../COMMISSIONING.md)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual installer artifacts, initial trust material and management recovery paths are not supplied by the generic modules.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
