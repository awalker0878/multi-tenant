# ADR-0038 — Govern images and privileged dependency provenance across their lifecycle

**Status:** Proposed<br>
**Accountable role:** Platform lifecycle and software supply-chain owners<br>
**Scope:** Portable hosting infrastructure service and supporting privileged execution<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md)

New source-backed proposed clarification from the named architecture sections; no historical acceptance is asserted. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

A version pin does not alone establish a trusted artifact, continuing support or a safe response after a compromised package has already run.

## Decision recorded in the source

Accept source provenance, digests, support/compatibility and revocation procedures for images, firmware, provider/module packages and privileged runner dependencies. Bind actual package identities to qualified change records and assess already-executed artifacts/credentials when trust is withdrawn.

## Alternatives and limits recorded in the source

This record makes an existing source obligation explicit; it does not claim a previously held alternatives meeting. A vendor-specific implementation is accepted only with supported native evidence and the relevant owner decision.

## Consequences

Keep approved root provider locks in Git and module/runner versions pinned separately. Quarantine revoked images at new-placement admission, stage upgrades and test recovery; do not declare all pinned dependencies permanently safe.

## Engineering and implementation obligations

Assign the actual service owner, native mechanism, failure/recovery path, scoped access and independent verification for each requirement. Record unimplemented/external controls rather than linking a generic module as proof.

## Requirement and code traceability

[SUP-001](../assurance/requirements.md#SUP-001) · [VULN-001](../assurance/requirements.md#VULN-001) · [VULN-002](../assurance/requirements.md#VULN-002) · [TF-005](../assurance/requirements.md#TF-005)

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform](../../terraform)
- [config/toolchain.json](../../config/toolchain.json)
- [tools/verify_terraform.py](../../tools/verify_terraform.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Concrete service parameters, installed components and organizational acceptance remain open. Local tests and repository merge do not qualify the native capability.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
