# 38. Bare metal, containers and future platforms

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13367_1645000677"></a>
<a id="sec_38"></a>

Bare-metal workloads can use the same WSD contract when their physical attachment, lifecycle, identity, storage and boundary controls are qualified. If the physical fabric provides their L3 domain, declare a fabric-routed service class and route its changes through foundation automation. This is a published realization path, not an undisclosed exception to routine overlay lifecycle. Bare-metal reuse includes firmware/boot control, BMC separation and media sanitization.

A Kubernetes namespace is an administrative scope, not by itself a complete hostile-tenant or security-zone boundary. A container profile must qualify API/RBAC, workload admission, node/host isolation, network-policy enforcement, privileged/host-network restrictions, secrets, storage, image provenance and recovery. Kubernetes documentation separately discusses multi-tenancy and the dependence of NetworkPolicy on the networking implementation. \[[S25](77-appendix-h-primary-sources-and-implementation-references.md#S25); [S26](77-appendix-h-primary-sources-and-implementation-references.md#S26)\]

The portable model does not require every platform to expose the same topology or every optional feature. A dedicated cluster, namespace, virtual control plane or other pattern is selected by the threat/assurance analysis. Declared extensions include accelerators, passthrough, unusual packet processing and stateful application features. A future platform joins only after passing the relevant conformance profile and providing an exit/recovery path; it is not admitted because its API resembles an existing target.

<a id="req_FUT_001"></a>

FUT-001  A new platform SHALL pass the applicable conformance suite before it is approved for production placement.

Platform engineering  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-065](73-appendix-d-conformance-test-catalogue.md#test_CT_065), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_FUT_002"></a>

FUT-002  A platform SHALL declare unsupported capabilities explicitly; unsupported capabilities SHALL NOT be emulated by weakening a mandatory control.

Platform engineering  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-065](73-appendix-d-conformance-test-catalogue.md#test_CT_065)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_FUT_003"></a>

FUT-003  Bare-metal and container profiles SHALL explicitly qualify host/control-plane, network, storage and lifecycle isolation; namespaces, projects and physical VRFs SHALL NOT alone be accepted as evidence of a complete security boundary.

Platform engineering  \|  Verify: [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-037](73-appendix-d-conformance-test-catalogue.md#test_CT_037), [CT-059](73-appendix-d-conformance-test-catalogue.md#test_CT_059), [CT-065](73-appendix-d-conformance-test-catalogue.md#test_CT_065), [CT-072](73-appendix-d-conformance-test-catalogue.md#test_CT_072)  \|  Basis: [S25](77-appendix-h-primary-sources-and-implementation-references.md#S25) / [S26](77-appendix-h-primary-sources-and-implementation-references.md#S26)  \|  new-v1.1

[Previous chapter](37-openstack-implementation-profile.md) · [Chapter index](README.md) · [Next chapter](43-part-v-service-control-plane-and-automation.md)
