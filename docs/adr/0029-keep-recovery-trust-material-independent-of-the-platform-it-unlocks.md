# ADR-0029 — Keep recovery trust material independent of the platform it unlocks

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [OPS §2](../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

The only identity or key needed to recover a failed encrypted platform cannot depend exclusively on that same unavailable platform.

## Decision recorded in the source

Separate human, automation, workload and recovery identities; distinguish key use, administration, recovery and destruction. Provide a controlled independent path to minimum bootstrap trust material.

## Alternatives and limits recorded in the source

Qualified cache and emergency behaviour must be explicitly recorded. Plaintext fallback, disabled certificate validation or an unrestricted replacement key is not a recovery design.

## Consequences

Key destruction can make retained copies unrecoverable. Administrative access, data location, support access, diagnostics and key custody remain independently constrained.

## Engineering and implementation obligations

Map trust dependencies and authority, actual credential rotation/revocation, approved emergency access and independent key/state/catalogue recovery.

## Requirement and code traceability

[IAM-001](../assurance/requirements.md#IAM-001) · [IAM-002](../assurance/requirements.md#IAM-002) · [CRY-001](../assurance/requirements.md#CRY-001) · [CRY-002](../assurance/requirements.md#CRY-002) · [CRY-003](../assurance/requirements.md#CRY-003) · [REC-001](../assurance/requirements.md#REC-001)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [lab/mtls_fixture.py](../../lab/mtls_fixture.py)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Local certificate and service-identity fixtures do not establish enterprise federation, revocation infrastructure, HSM/KMS or actual bootstrap custody.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
