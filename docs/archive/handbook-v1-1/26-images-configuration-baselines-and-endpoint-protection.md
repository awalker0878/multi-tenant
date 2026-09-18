# 26. Images, configuration baselines and endpoint protection

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:407 BEGIN -->

<a id="__RefHeading___Toc13341_1645000677"></a>
<a id="sec_26"></a>

<!-- SOURCE-BLOCK HB11:407 END -->

<!-- SOURCE-BLOCK HB11:408 BEGIN -->

Approved images and host baselines are versioned service inputs. An ImageProfile identifies operating system, build source, signed digest, boot mode, drivers/agents, hardening baseline, vulnerability disposition, software inventory and support lifecycle. The image pipeline separates building, approving, publishing and deployment. Tenant customization remains inside the declared baseline; changes that disable required protection or expose management interfaces are denied or formally excepted.

<!-- SOURCE-BLOCK HB11:408 END -->

<!-- SOURCE-BLOCK HB11:409 BEGIN -->

The baseline covers firmware, hypervisor, controller, guest, network/security appliances and automation runners. Harden to necessary functionality, configure authenticated time/logging, remove default credentials, restrict consoles and administrative protocols, and enable supported endpoint monitoring/antimalware as required. An agent must not be installed on a hypervisor contrary to vendor support; use the qualified platform-native protection when appropriate. Supported and tested versions, asset lifecycle and hardening are explicit elements of the applicable GC configuration guidance. \[[S07](77-appendix-h-primary-sources-and-implementation-references.md#S07), sections 1-3\]

<!-- SOURCE-BLOCK HB11:409 END -->

<!-- SOURCE-BLOCK HB11:410 BEGIN -->

Image signing does not prove the image is safe; it links the deployed bytes to an accountable build. Qualification verifies both provenance and runtime configuration. Rebuild cadence and vulnerability triggers invalidate retired images, and deployed drift is reconciled rather than hidden by a clean image label. Guest workloads retain responsibility for application libraries, service accounts and data handling that infrastructure automation cannot determine.

<!-- SOURCE-BLOCK HB11:410 END -->

<!-- SOURCE-BLOCK HB11:411 BEGIN -->

<a id="req_IMG_001"></a>

IMG-001  Only approved versioned images and baselines SHALL be deployed; each SHALL include provenance, digest, support status, hardening and vulnerability disposition with a retirement/rebuild policy.

<!-- SOURCE-BLOCK HB11:411 END -->

<!-- SOURCE-BLOCK HB11:412 BEGIN -->

Platform engineering  \|  Verify: [CT-036](73-appendix-d-conformance-test-catalogue.md#test_CT_036), [CT-040](73-appendix-d-conformance-test-catalogue.md#test_CT_040), [CT-041](73-appendix-d-conformance-test-catalogue.md#test_CT_041)  \|  Basis: [S07](77-appendix-h-primary-sources-and-implementation-references.md#S07)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:412 END -->

<!-- SOURCE-BLOCK HB11:413 BEGIN -->

<a id="req_IMG_002"></a>

IMG-002  Runtime configuration SHALL be verified against the required baseline after provisioning and material change; unsupported protection agents or disabled mandatory controls SHALL not be silently accepted.

<!-- SOURCE-BLOCK HB11:413 END -->

<!-- SOURCE-BLOCK HB11:414 BEGIN -->

Platform engineering  \|  Verify: [CT-014](73-appendix-d-conformance-test-catalogue.md#test_CT_014), [CT-036](73-appendix-d-conformance-test-catalogue.md#test_CT_036), [CT-040](73-appendix-d-conformance-test-catalogue.md#test_CT_040)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:414 END -->

[Previous chapter](25-cryptography-kms-certificates-and-crypto-agility.md) · [Chapter index](README.md) · [Next chapter](27-backup-retention-and-isolated-restore.md)
