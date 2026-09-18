# ADR-0014 — Bootstrap management and trust before consuming native APIs

**Status:** Proposed<br>
**Accountable role:** Automation platform / Management operations / Continuity management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-12`<br>
**Source chapters:** [RA §21](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PBS §1](../engineering/platform-build/1-choose-the-platform-boundary-and-configuration-owner.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

An empty site cannot already depend on the APIs, identity, DNS, key service and state backend that it is being asked to build.

## Decision

Use supported hardware/platform installers and lifecycle tools to establish restricted management, trust and native APIs. Let Terraform manage supported resource operations after those prerequisites exist.

## Alternatives and source limitations

Temporary external bootstrap dependencies are allowed with named owners and a controlled transfer to steady state. An unsupported shell action inside Terraform is not equivalent to a supported declarative resource.

## Consequences

Some installation tasks can proceed in parallel, but tenant allocation must not consume unaccepted security, storage or management foundations. Bootstrap cleanup must not erase the only usable recovery material.

## Engineering and implementation obligations

Document dependency cuts, temporary credentials, verified artifacts, native operation coverage and accepted handover; revoke temporary grants after successful transfer.

## Requirement and code traceability

[AUTO-001](../assurance/requirements.md#AUTO-001) · [MGT-005](../assurance/requirements.md#MGT-005) · [REC-001](../assurance/requirements.md#REC-001) · [QUAL-001](../assurance/requirements.md#QUAL-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/README.md](../../terraform/README.md)
- [docs/COMMISSIONING.md](../COMMISSIONING.md)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual installer artifacts, initial trust material and management recovery paths are not supplied by the generic modules.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
