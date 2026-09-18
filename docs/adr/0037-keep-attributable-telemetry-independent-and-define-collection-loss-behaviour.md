# ADR-0037 — Keep attributable telemetry independent and define collection-loss behaviour

**Status:** Proposed<br>
**Accountable role:** Platform, telemetry and security service owners<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md)

New source-derived synthesis for an audit-identified implicit decision, not a recovered prior meeting or an issued approval.
> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.


## Context

Tenant health and a shared logging transport cannot alone establish independent enforcement evidence. Collection can fail while data-plane controls continue.

## Decision

Collect provider-controlled policy, route, identity, data-copy and privileged-action evidence with stable scope identifiers. Define separate source and receipt time, controlled access/minimization/retention, buffering, visible loss and safe operating restrictions when collection is unavailable.

## Alternatives and source limitations

The source does not select a logging product or mandate payload capture. Monitoring solely inside the tenant or treating the absence of logs as successful enforcement is not accepted evidence.

## Consequences

A shared collector remains a security and recovery dependency with its own authority and capacity. An outage must not silently enable a permit path; the accepted profile determines whether new changes pause and how buffering/loss are handled.

## Engineering and implementation obligations

Name actual collectors, routes, role scopes, integrity/retention controls, identifiers, time handling, queue/loss limits and escalation. Test the defined collection outage and recovery separately from the data path.

## Requirement and code traceability

[OBS-001](../assurance/requirements.md#OBS-001) · [OBS-002](../assurance/requirements.md#OBS-002) · [OBS-003](../assurance/requirements.md#OBS-003) · [FAIL-001](../assurance/requirements.md#FAIL-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [docs/operations/README.md](../operations/README.md)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Native telemetry, access controls, buffering and operating restrictions remain external implementation/qualification work. No collection availability or incident authority is established by this ADR.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
