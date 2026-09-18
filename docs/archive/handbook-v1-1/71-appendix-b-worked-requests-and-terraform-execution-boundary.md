# Appendix B — Worked requests and Terraform execution boundary

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13427_1645000677"></a>
<a id="app_B"></a>

<a id="__RefHeading___Toc13429_1645000677"></a>

## Reference examples and migration

This sample request is schema-validated and references the consistent example bundle in the companion package. It is not production-ready: its associated profiles are Proposed/Candidate, no authorization has been issued and no live evidence exists. The application has OZ and RZ intent, one declared database flow, a DNS binding and no public/Internet exposure. The entire bundle supplies the profile, domain, flow and binding definitions needed to interpret it.

```text
apiVersion: hosting.platform/v1.1kind: WorkloadSecurityDomainmetadata:  name: application-prod  namespace: tenant-001  ownerRef: reference-owner-not-assigned  version: 1.0.0spec:  tenantRef:    kind: TenantNamespace    name: tenant-001    version: 1.0.0  categorization:    confidentiality: ProtectedB    integrity: Medium    availabilityImpact: Medium  securityProfileRef:    kind: SecurityProfile    name: security-reference    version: 1.0.0  assuranceProfileRef:    kind: AssuranceProfile    name: assurance-reference    version: 1.0.0  placementProfileRef:    kind: PlacementProfile    name: placement-reference    version: 1.0.0  availabilityProfileRef:    kind: AvailabilityProfile    name: availability-reference    version: 1.0.0  computeProfileRef:    kind: ComputeProfile    name: compute-reference    version: 1.0.0  storageProfileRefs:  - kind: StorageProfile    name: storage-reference    version: 1.0.0  backupPolicyRef:    kind: BackupPolicy    name: backup-reference    version: 1.0.0  evidenceProfileRef:    kind: EvidenceProfile    name: evidence-reference    version: 1.0.0  domains:  - name: operations    zoneClass: OZ    domainRef:      kind: SecurityDomain      name: operations-domain      version: 1.0.0  - name: restricted    zoneClass: RZ    domainRef:      kind: SecurityDomain      name: restricted-domain      version: 1.0.0  networks:  - name: frontend    domainName: operations    ipv4PrefixSize: 24    ipv6Mode: dual-stack  - name: database    domainName: restricted    ipv4PrefixSize: 24    ipv6Mode: dual-stack  flowRefs:  - kind: FlowIntent    name: flowintent-reference    version: 1.0.0  serviceBindingRefs:  - kind: ServiceBinding    name: servicebinding-reference    version: 1.0.0  exposureRefs: []  lifecycleIntent: Active
```

### Reading a FlowIntent

```text
kind: FlowIntentspec:  wsdRef:    kind: WorkloadSecurityDomain    name: application-prod    version: 1.0.0  source:    type: network    name: frontend  destination:    type: network    name: database  flowProfileRef:    kind: FlowProfile    name: flow-reference    version: 1.0.0  direction: source-to-destination  justification: Application tier accesses the approved database service  validFrom: '2026-09-16T00:00:00Z'  expiresAt: '2027-01-01T00:00:00Z'  loggingRequired: true
```

The referenced FlowProfile specifies TCP/5432, stateful request/reply, required TLS and logging. Admission still resolves identities, checks both zone authorities, selects a qualified ZIP path and tests effective policy. A flow reference is not itself evidence that connectivity has been approved or configured.

### Terraform root configuration pattern

The following is a syntactically concrete configuration pattern, not a deployable adapter or a certified stack. Provider version 2.4.2 is used only as the documentation snapshot example recorded in [S17](77-appendix-h-primary-sources-and-implementation-references.md#S17). Replace it through an approved compatibility/qualification decision, initialize and review the actual lock file, and supply a supported endpoint and credentials through the approved runner. The password input is ephemeral in a compatible Terraform runtime; provider behavior and all persisted artifacts still require verification. \[[S13](77-appendix-h-primary-sources-and-implementation-references.md#S13)–[S17](77-appendix-h-primary-sources-and-implementation-references.md#S17)\]

```text
terraform {  required_version = ">= 1.11, < 2.0"  required_providers {    nutanix = {      source  = "nutanix/nutanix"      version = "= 2.4.2"    }  }}variable "pc_endpoint" { type = string }variable "pc_username" { type = string }variable "pc_password" {  type      = string  sensitive = true  ephemeral = true}provider "nutanix" {  endpoint = var.pc_endpoint  username = var.pc_username  password = var.pc_password  insecure = false}# Native resources/modules are supplied by the qualified adapter.# Child modules declare required_providers and receive this provider.# No production credentials or native resources are included here.
```

A provider lock file covers provider selections and checksums, not remote module versions. Pin module versions or immutable source commits separately. Do not replace missing adapters with an empty root and label its successful plan a hosting deployment. The orchestrator manages admission, placement, approval, staged authority-specific apply, realization and evidence; Terraform is only one actuator. \[[S14](77-appendix-h-primary-sources-and-implementation-references.md#S14)\]

### Contract migration from the illustrative v1.0 draft

Move the original top-level intent fields under spec; replace ambiguous protected-b-medium and availability strings with independent impact classification and typed profile references. Split logical domains from site/platform instances, replace REZ internal enums with ExternalDomain, replace boolean service/exposure flags with typed binding/exposure references, and deny consumer writes to observed status. These are breaking semantic changes requiring controlled translation, dependency resolution, validation and re-admission. Do not silently mutate a deployed API or relabel v1.0 records as validated v1.1.

[Previous chapter](70-appendix-a-canonical-object-contract-and-api-surface.md) · [Chapter index](README.md) · [Next chapter](72-appendix-c-complete-normative-requirement-and-verification-index.md)
