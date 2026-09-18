# 5. Threat and Trust Model

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:74 BEGIN -->

<!-- SOURCE-BLOCK HB10:74 END -->

<!-- SOURCE-BLOCK HB10:75 BEGIN -->

The design assumes that tenant workloads, platform APIs, external networks, shared services, and management systems do not share a single trust level. It assumes configuration mistakes, compromised workloads, over-permissive routes, provider drift, and operator error are realistic threats. Controls therefore aim to make unsafe connectivity structurally difficult rather than relying only on administrator discipline.

<!-- SOURCE-BLOCK HB10:75 END -->

<!-- SOURCE-BLOCK HB10:76 BEGIN -->

## 5.1 Principal Threats

<!-- SOURCE-BLOCK HB10:76 END -->

<!-- SOURCE-BLOCK HB10:77 BEGIN -->

- Cross-tenant lateral movement caused by route leakage, shared-policy mistakes, or permissive defaults.

<!-- SOURCE-BLOCK HB10:77 END -->

<!-- SOURCE-BLOCK HB10:78 BEGIN -->

- Inter-zone bypass caused by direct platform routing, generic transit VRFs, or broad shared-services reachability.

<!-- SOURCE-BLOCK HB10:78 END -->

<!-- SOURCE-BLOCK HB10:79 BEGIN -->

- Management-plane compromise through workload-to-management connectivity.

<!-- SOURCE-BLOCK HB10:79 END -->

<!-- SOURCE-BLOCK HB10:80 BEGIN -->

- Uncontrolled public ingress or Internet egress.

<!-- SOURCE-BLOCK HB10:80 END -->

<!-- SOURCE-BLOCK HB10:81 BEGIN -->

- IPv6 or alternate path bypass when only IPv4 is tested.

<!-- SOURCE-BLOCK HB10:81 END -->

<!-- SOURCE-BLOCK HB10:82 BEGIN -->

- Automation identities with excessive privileges or shared credentials.

<!-- SOURCE-BLOCK HB10:82 END -->

<!-- SOURCE-BLOCK HB10:83 BEGIN -->

- Configuration drift outside the infrastructure-as-code workflow.

<!-- SOURCE-BLOCK HB10:83 END -->

<!-- SOURCE-BLOCK HB10:84 BEGIN -->

- Failure-state bypass caused by security controls failing open.

<!-- SOURCE-BLOCK HB10:84 END -->

<!-- SOURCE-BLOCK HB10:85 BEGIN -->

- Platform portability claims that silently downgrade security on a less capable platform.

<!-- SOURCE-BLOCK HB10:85 END -->

<!-- SOURCE-BLOCK HB10:86 BEGIN -->

<!-- SOURCE-BLOCK HB10:86 END -->

[Previous chapter](4-core-conceptual-model.md) · [Chapter index](README.md) · [Next chapter](09-part-ii-reference-architecture.md)
