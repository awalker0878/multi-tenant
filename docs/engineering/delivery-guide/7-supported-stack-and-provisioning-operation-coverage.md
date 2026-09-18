# 7. Supported stack and provisioning operation coverage

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<a id="EK_07"></a>

Use one support record for the exact installed combination and a separate operation matrix for what the tools can actually manage. Documentation availability is not measured qualification.

Baseline and related records: [VND §7](../platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)  •  [PROV §3](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [VC §7](../vendor-cards/7-support-tuple-variations-and-evidence-checklist.md#VC_07)  •  [ET §8](../../templates/lld/8-exact-platform-and-tool-operation-coverage.md#ET_08)


<a id="source-table-69"></a>

| Support dimension | Evidence to capture |
| --- | --- |
| Installed tuple | Hardware/NIC/firmware, OS/hypervisor, managers, network backend, storage/protection, APIs, provider/installer versions and enabled entitlements. |
| Operation coverage | Observe, create, update, adopt/import, replace, delete and discover uncertain outcome per native resource family. |
| Single writer | Exactly which tool/team owns the native object and any independently managed subresource; protected handoff boundaries. |
| Lifecycle semantics | Asynchronous completion, retry/discovery, replacement/destruction, upgrade/rollback constraints and cleanup. |
| Reproducibility | Trusted package provenance, reviewed provider lock, separately fixed module/runner versions, artifact integrity and controlled credentials. |
| Unsupported case | Supported native alternative with owner/evidence, or excluded capability. No shim or empty root is called complete provisioning. |

HashiCorp documents provider configurations and inheritance within modules, while provider dependency locks do not lock remote module versions. Keep those controls separate in the engineering release. \[K03, K04\]

External mechanism context: [K03 — Terraform providers within modules](https://developer.hashicorp.com/terraform/language/modules/develop/providers)  •  [K04 — Terraform dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock)

[Previous chapter](6-capacity-mtu-performance-and-failure-analysis.md) · [Chapter index](README.md) · [Next chapter](8-build-test-and-implementation-handoff.md)
