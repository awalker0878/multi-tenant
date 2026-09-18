# ADR-0014 — Bootstrap management and trust before consuming native APIs

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-12`<br>
**Source chapters:** [RA §21](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [PBS §1](../engineering/platform-build/1-choose-the-platform-boundary-and-configuration-owner.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/README.md](../../terraform/README.md)
- [docs/COMMISSIONING.md](../COMMISSIONING.md)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual installer artifacts, initial trust material and management recovery paths are not supplied by the generic modules.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
