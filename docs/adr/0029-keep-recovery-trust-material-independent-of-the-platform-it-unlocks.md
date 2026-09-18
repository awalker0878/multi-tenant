# ADR-0029 — Keep recovery trust material independent of the platform it unlocks

**Status:** Proposed<br>
**Accountable role:** Identity operations / Security authority / Key-management operations<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [OPS §2](../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.
> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.


## Context

The only identity or key needed to recover a failed encrypted platform cannot depend exclusively on that same unavailable platform.

## Decision

Separate human, automation, workload and recovery identities; distinguish key use, administration, recovery and destruction. Provide a controlled independent path to minimum bootstrap trust material.

## Alternatives and source limitations

Qualified cache and emergency behaviour must be explicitly recorded. Plaintext fallback, disabled certificate validation or an unrestricted replacement key is not a recovery design.

## Consequences

Key destruction can make retained copies unrecoverable. Administrative access, data location, support access, diagnostics and key custody remain independently constrained.

Adopt a versioned cryptographic configuration for actual clients, protocols, trust stores and key custody. Separate key use from administration/destruction; record rotation, revocation, unsupported-protocol handling and recoverable key availability. Example algorithms or a local TLS test are not a qualified cryptographic module or enterprise KMS.

## Engineering and implementation obligations

Map trust dependencies and authority, actual credential rotation/revocation, approved emergency access and independent key/state/catalogue recovery. Validate these dependencies and record their owner, accepted configuration and failure/recovery observations before the affected service is offered.

## Requirement and code traceability

[IAM-001](../assurance/requirements.md#IAM-001) · [IAM-002](../assurance/requirements.md#IAM-002) · [CRY-001](../assurance/requirements.md#CRY-001) · [CRY-002](../assurance/requirements.md#CRY-002) · [CRY-003](../assurance/requirements.md#CRY-003) · [REC-001](../assurance/requirements.md#REC-001) · [SEC-003](../assurance/requirements.md#SEC-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [lab/mtls_fixture.py](../../lab/mtls_fixture.py)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Local certificate and service-identity fixtures do not establish enterprise federation, revocation infrastructure, HSM/KMS or actual bootstrap custody.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
