# 45. Secrets and automation credentials

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:618 BEGIN -->

<a id="__RefHeading___Toc13383_1645000677"></a>
<a id="sec_45"></a>

<!-- SOURCE-BLOCK HB11:618 END -->

<!-- SOURCE-BLOCK HB11:619 BEGIN -->

Credentials are injected by the authorized execution environment or a credential broker, never embedded in repository files. Prefer task-scoped short-lived credentials where the target supports them. Where a provider requires a longer-lived credential, document the residual exposure, vault it, restrict egress, rotate it and monitor its use. A “sensitive” Terraform flag can redact display without preventing storage in state; classification and backend protection still apply.

<!-- SOURCE-BLOCK HB11:619 END -->

<!-- SOURCE-BLOCK HB11:620 BEGIN -->

Terraform ephemeral values and supported write-only resource arguments can reduce persisted secret exposure, but their availability and behavior depend on the Terraform version and provider/resource implementation. Use them only where verified and test the actual plan/state/log artifacts with disposable sentinel secrets. They do not guarantee that an entire provider cannot persist a secret. \[[S15](77-appendix-h-primary-sources-and-implementation-references.md#S15); [S16](77-appendix-h-primary-sources-and-implementation-references.md#S16)\]

<!-- SOURCE-BLOCK HB11:620 END -->

<!-- SOURCE-BLOCK HB11:621 BEGIN -->

Runners are short-lived and isolated per authority domain. Restrict network reachability to required APIs, verify endpoint TLS identity, avoid disabling certificate validation and remove workspace artifacts after protected retention decisions. Credential revocation is tested at the target service. Break-glass secrets, source signing keys, evidence signing keys and state-backend credentials are separated to limit compromise propagation.

<!-- SOURCE-BLOCK HB11:621 END -->

<!-- SOURCE-BLOCK HB11:622 BEGIN -->

<a id="req_SEC_001"></a>

SEC-001  Static privileged provider credentials SHALL NOT be embedded in Terraform source code.

<!-- SOURCE-BLOCK HB11:622 END -->

<!-- SOURCE-BLOCK HB11:623 BEGIN -->

Automation platform  \|  Verify: [CT-043](73-appendix-d-conformance-test-catalogue.md#test_CT_043)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:623 END -->

<!-- SOURCE-BLOCK HB11:624 BEGIN -->

<a id="req_SEC_002"></a>

SEC-002  Automation identities SHALL use least privilege and separate duties by control domain.

<!-- SOURCE-BLOCK HB11:624 END -->

<!-- SOURCE-BLOCK HB11:625 BEGIN -->

Automation platform  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044), [CT-079](73-appendix-d-conformance-test-catalogue.md#test_CT_079)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:625 END -->

<!-- SOURCE-BLOCK HB11:626 BEGIN -->

<a id="req_SEC_003"></a>

SEC-003  Credential rotation, revocation, and break-glass recovery SHALL be tested as part of the platform operational profile.

<!-- SOURCE-BLOCK HB11:626 END -->

<!-- SOURCE-BLOCK HB11:627 BEGIN -->

Automation platform  \|  Verify: [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027), [CT-028](73-appendix-d-conformance-test-catalogue.md#test_CT_028), [CT-043](73-appendix-d-conformance-test-catalogue.md#test_CT_043)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:627 END -->

<!-- SOURCE-BLOCK HB11:628 BEGIN -->

<a id="req_SEC_004"></a>

SEC-004  Where supported and verified, sensitive values SHOULD use ephemeral/write-only mechanisms; all remaining secret-bearing plan/state/log artifacts SHALL be classified, encrypted, access-controlled and tested for unintended disclosure.

<!-- SOURCE-BLOCK HB11:628 END -->

<!-- SOURCE-BLOCK HB11:629 BEGIN -->

Automation platform  \|  Verify: [CT-043](73-appendix-d-conformance-test-catalogue.md#test_CT_043), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044)  \|  Basis: [S15](77-appendix-h-primary-sources-and-implementation-references.md#S15) / [S16](77-appendix-h-primary-sources-and-implementation-references.md#S16)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:629 END -->

[Previous chapter](44-ci-cd-signed-plans-and-supply-chain-integrity.md) · [Chapter index](README.md) · [Next chapter](46-drift-emergency-overrides-and-desired-state-convergence.md)
