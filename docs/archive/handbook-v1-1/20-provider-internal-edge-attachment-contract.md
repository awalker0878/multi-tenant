# 20. Provider-internal Edge Attachment contract

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:341 BEGIN -->

<a id="__RefHeading___Toc13327_1645000677"></a>
<a id="sec_20"></a>

<!-- SOURCE-BLOCK HB11:341 END -->

<!-- SOURCE-BLOCK HB11:342 BEGIN -->

An EdgeAttachment is the provider-internal interface between a Security Domain Instance and a ZIP, approved service or external-domain boundary. It is not a consumer VLAN request. The same contract can be realized as a routed virtual gateway attachment, controlled external subnet, scoped segment or physical interface context. Attachment pools may be commissioned in advance; allocation of a pool slot remains an auditable lifecycle action.

<!-- SOURCE-BLOCK HB11:342 END -->

<!-- SOURCE-BLOCK HB11:343 BEGIN -->


<a id="source-table-343"></a>

| Required field group | Engineering content |
| --- | --- |
| Identity and ownership | Attachment ID, domain/instance, endpoint relationship, owner, service class and operation generation |
| Transport | Address families, workload MTU, encapsulation budget, physical/virtual endpoint and transport dependencies |
| Forwarding | Routing protocol/static policy, next-hop authority, accepted/advertised prefix sets, maximum route count and summaries |
| Isolation | Dedicated/shared context, source identity, anti-spoofing, same-segment bypass controls and NAT/PBR behavior |
| Resilience | Failure domains, active/standby or active/active behavior, session symmetry, fencing and failover bounds |
| Evidence | Configuration digests, effective paths, capacity reservation, qualification record and cleanup receipts |

<!-- SOURCE-BLOCK HB11:343 END -->

<!-- SOURCE-BLOCK HB11:344 BEGIN -->

The most dangerous shortcut is to place independent domains on a common connected external network and assume the downstream firewall will inspect every packet. Direct forwarding, ARP/ND, a connected gateway or hairpin NAT may avoid it. Shared attachments are therefore admitted only after CT-023 and CT-024 demonstrate identity preservation, enforced paths and return behavior. Where that proof is unavailable, use dedicated contexts rather than relaxing the contract.

<!-- SOURCE-BLOCK HB11:344 END -->

<!-- SOURCE-BLOCK HB11:345 BEGIN -->

<a id="req_EDGE_001"></a>

EDGE-001  Every domain-to-boundary attachment SHALL have a provider-owned EdgeAttachment record covering forwarding authority, isolation, MTU, HA, capacity and cleanup; consumers SHALL NOT choose its native topology identifiers.

<!-- SOURCE-BLOCK HB11:345 END -->

<!-- SOURCE-BLOCK HB11:346 BEGIN -->

Network engineering  \|  Verify: [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024), [CT-032](73-appendix-d-conformance-test-catalogue.md#test_CT_032), [CT-071](73-appendix-d-conformance-test-catalogue.md#test_CT_071)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:346 END -->

<!-- SOURCE-BLOCK HB11:347 BEGIN -->

<a id="req_EDGE_002"></a>

EDGE-002  A shared attachment SHALL be prohibited unless direct connected, neighbor, gateway and NAT/PBR paths preserve the required domain isolation and ZIP enforcement in normal and failure states.

<!-- SOURCE-BLOCK HB11:347 END -->

<!-- SOURCE-BLOCK HB11:348 BEGIN -->

Security authority  \|  Verify: [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:348 END -->

[Previous chapter](19-microsegmentation-labels-and-workload-attachment.md) · [Chapter index](README.md) · [Next chapter](21-multi-site-domains-and-recovery-connectivity.md)
