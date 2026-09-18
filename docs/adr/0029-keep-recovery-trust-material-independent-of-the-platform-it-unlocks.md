# ADR-0029 — Keep recovery trust material independent of the platform it unlocks

**Status:** Proposed<br>
**Accountable role:** Cryptographic policy and key-service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [PROV §2](../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md) · [OPS §2](../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [lab/mtls_fixture.py](../../lab/mtls_fixture.py)
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Local certificate and service-identity fixtures do not establish enterprise federation, revocation infrastructure, HSM/KMS or actual bootstrap custody.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

## Proposed clarification — Versioned cryptographic policy and service protocol lifecycle

Specify the adopted algorithm/protocol versions, actual clients, key ownership, certificate issuance/renewal, revocation, independent recovery and destruction/retention responsibilities. Select concrete parameters only through the applicable policy and native support review. Recovery material alone does not complete cryptographic service design.

Source basis: [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md). This clarification is not an accepted historical decision.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
