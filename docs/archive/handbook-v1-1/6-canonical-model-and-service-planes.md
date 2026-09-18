# 6. Canonical model and service planes

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:171 BEGIN -->

<a id="__RefHeading___Toc13297_1645000677"></a>
<a id="sec_6"></a>

<!-- SOURCE-BLOCK HB11:171 END -->

<!-- SOURCE-BLOCK HB11:172 BEGIN -->

The durable contract is the WSD intent, not a physical topology. A Tenant Namespace owns administrative scope; a WSD owns workload lifecycle and desired outcomes; a logical Security Domain owns one zone class and security authority; a Security Domain Instance realizes that domain at a particular site and platform. A Network belongs to exactly one instance. A workload may use several networks only where its role and non-transit behavior are explicitly authorized.

<!-- SOURCE-BLOCK HB11:172 END -->

<!-- SOURCE-BLOCK HB11:173 BEGIN -->

Separate the workload data plane, provider service-consumption plane, platform control plane, privileged management plane, OOB transport and physical underlay. A provider area is therefore a set of governed services and administrative boundaries, not one universally reachable “provider VRF”. Shared DNS or backup consumption never implies access to Prism, NSX Manager, OpenStack administrative APIs, storage controllers or BMC interfaces.

<!-- SOURCE-BLOCK HB11:173 END -->

<!-- SOURCE-BLOCK HB11:174 BEGIN -->

![Tenant Namespace contains WSD lifecycle intent. WSD references one or more logical Security Domains. Each domain has site/platform-specific instances and workload networks. ZIP relationships mediate instance or external-domain transitions. Provider services and privileged management are separate planes, not parent transit networks.](../../assets/diagrams/d23524425c4dfcd4c90b.png)

<!-- SOURCE-BLOCK HB11:174 END -->

<!-- SOURCE-BLOCK HB11:175 BEGIN -->

<a id="fig_model"></a>

Figure 1. The portable object model and independent provider planes

<!-- SOURCE-BLOCK HB11:175 END -->

<!-- SOURCE-BLOCK HB11:176 BEGIN -->

The addition of a logical Security Domain removes the old ambiguity between a security authority and a site-specific routing object. Multiple WSDs may share a domain only when the same authority and an approved sharing policy allow it. The shared domain is not destroyed when one WSD retires; dependency references and a domain owner control its lifecycle. Native platform identifiers are stored in provider status and evidence, never as routine consumer inputs.

<!-- SOURCE-BLOCK HB11:176 END -->

<!-- SOURCE-BLOCK HB11:177 BEGIN -->

<a id="req_MODEL_001"></a>

MODEL-001  Every network SHALL resolve to one Security Domain Instance, one logical domain, one zone class, one address authority and one accountable owner; shared-domain lifecycle SHALL use explicit dependency references.

<!-- SOURCE-BLOCK HB11:177 END -->

<!-- SOURCE-BLOCK HB11:178 BEGIN -->

Architecture authority  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:178 END -->

<!-- SOURCE-BLOCK HB11:179 BEGIN -->

<a id="req_MODEL_002"></a>

MODEL-002  Provider service consumption, platform control, privileged management and OOB transport SHALL be modeled separately; a shared service SHALL NOT create implicit authority over another plane.

<!-- SOURCE-BLOCK HB11:179 END -->

<!-- SOURCE-BLOCK HB11:180 BEGIN -->

Architecture authority  \|  Verify: [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-008](73-appendix-d-conformance-test-catalogue.md#test_CT_008), [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:180 END -->

<!-- SOURCE-BLOCK HB11:181 BEGIN -->

<!-- SOURCE-BLOCK HB11:181 END -->

[Previous chapter](5-threat-model-and-trust-boundaries.md) · [Chapter index](README.md) · [Next chapter](08-part-ii-portable-security-architecture.md)
