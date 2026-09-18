# 42. Terraform roots, adapters and reproducible inputs

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13377_1645000677"></a>
<a id="sec_42"></a>

Terraform is an actuator for an approved plan, not the consumer API, placement solver or authorization engine. The orchestrator selects a platform adapter before Terraform runs. Root modules configure providers and pass explicit aliases to focused child modules; reusable modules declare provider requirements rather than embedding credentials. Provider configuration in roots follows HashiCorp’s module guidance. \[[S13](77-appendix-h-primary-sources-and-implementation-references.md#S13)\]

Separate contracts, policy, registries, provider adapters, reusable modules, authority-specific root stacks, tests and evidence. A module interface represents one controlled lifecycle/authority scope. Do not create one giant cross-provider conditional module or a monolithic all-tenant state. Inputs are normalized JSON/YAML with secret references resolved only by the authorized runner. Native object IDs can appear in provider-internal outputs and evidence, not the public WSD contract.

```text
repository/  contracts/          # versioned object schemas and examples  profiles/           # controlled security/service/capability records  policy/             # admission, routing and readiness decisions  adapters/           # nutanix, nsx, openstack, qualified future targets  modules/            # provider-native, focused reusable resources  stacks/             # foundation, management, edge, domain, workload  tests/              # contract, semantic, integration, conformance  evidence/           # manifests and references; not plaintext secrets
```

Commit provider dependency lockfiles and verify package checksums. The Terraform lockfile does not lock remote module selections, so modules use immutable registry versions or full commit identifiers and a separately recorded source digest. The build/run environment is also pinned and scanned. Upgrades are explicit dependency changes with a canary plan and conformance tests, not automatic drift to a moving “latest” release. \[[S14](77-appendix-h-primary-sources-and-implementation-references.md#S14)\]

<a id="req_TF_001"></a>

TF-001  Provider configuration SHALL be defined in root modules and passed to child modules; reusable child modules SHOULD NOT embed provider credentials/configuration.

Automation platform  \|  Verify: [CT-042](73-appendix-d-conformance-test-catalogue.md#test_CT_042), [CT-043](73-appendix-d-conformance-test-catalogue.md#test_CT_043)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S13](77-appendix-h-primary-sources-and-implementation-references.md#S13)  \|  retained-v1.0

<a id="req_TF_002"></a>

TF-002  Provider versions SHALL be constrained and dependency lock files SHALL be committed and reviewed.

Automation platform  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-042](73-appendix-d-conformance-test-catalogue.md#test_CT_042), [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S14](77-appendix-h-primary-sources-and-implementation-references.md#S14)  \|  retained-v1.0

<a id="req_TF_003"></a>

TF-003  The orchestration layer SHALL select the provider adapter; a single giant conditional module SHOULD NOT attempt to implement all platforms.

Automation platform  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_TF_004"></a>

TF-004  Module interfaces SHOULD be relatively flat and composable; deeply nested modules that obscure lifecycle or ownership boundaries SHOULD be avoided.

Automation platform  \|  Verify: [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_TF_005"></a>

TF-005  Remote module sources and runner images SHALL be pinned to immutable versions/digests separately from provider lockfiles; approved package checksums and provenance SHALL be verified before privileged execution.

Automation platform  \|  Verify: [CT-042](73-appendix-d-conformance-test-catalogue.md#test_CT_042), [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048)  \|  Basis: [S14](77-appendix-h-primary-sources-and-implementation-references.md#S14)  \|  new-v1.1

[Previous chapter](41-zero-touch-provisioning-and-reconciliation-workflow.md) · [Chapter index](README.md) · [Next chapter](43-state-boundaries-cross-state-transactions-and-partial-failure.md)
