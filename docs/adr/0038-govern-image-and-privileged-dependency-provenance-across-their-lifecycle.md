# ADR-0038 — Govern image and privileged dependency provenance across their lifecycle

**Status:** Proposed<br>
**Accountable role:** Platform/image, execution and supply-chain service owners<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [RA §13](../architecture/reference/13-identity-cryptography-and-service-trust.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md)

New source-derived synthesis for an audit-identified implicit decision, not a recovered prior meeting or an issued approval.
> **Editorial extension:** this record includes a separately identified audit-remediation proposal grounded in its linked sources; no original approval is inferred.


## Context

Images, modules, plugins and runner artifacts influence privileged execution and can invalidate hardening or portability without changing the consumer request.

## Decision

Version and govern image/template publishing, provenance, support, hardening, vulnerability disposition and retirement. Keep builder, approver, signer and publisher authority explicit. Pin/review provider selections separately from module, runner and image identities, and reject untrusted or revoked artifacts from promotion.

## Alternatives and source limitations

The source permits platform-specific image variants with declared compatibility and exit limits. A product name, tag or image ID is not by itself proof of provenance, support or a valid baseline.

## Consequences

Trust material, artifact availability, revocation and recovery paths need independent owners. Committing a lock file records actual provider selections/checksums, not organization-wide supply-chain approval or native image security.

## Engineering and implementation obligations

Record allowed sources, identities/digests, signing/trust policy, approved platform variants, runtime configuration checks and rebuild/retirement conditions. Review the exact artifact change and affected native qualification.

## Requirement and code traceability

[IMG-001](../assurance/requirements.md#IMG-001) · [IMG-002](../assurance/requirements.md#IMG-002) · [TF-002](../assurance/requirements.md#TF-002) · [SEC-001](../assurance/requirements.md#SEC-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/verify_terraform.py](../../tools/verify_terraform.py)
- [terraform/modules/vsphere-workload/main.tf.json](../../terraform/modules/vsphere-workload/main.tf.json)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual approved image registries, signing policy, provenance service, guest hardening and vulnerability handling remain to be implemented and accepted. CI pins alone do not satisfy the whole decision.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
