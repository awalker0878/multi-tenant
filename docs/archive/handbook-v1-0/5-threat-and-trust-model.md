# 5. Threat and Trust Model

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
The design assumes that tenant workloads, platform APIs, external networks, shared services, and management systems do not share a single trust level. It assumes configuration mistakes, compromised workloads, over-permissive routes, provider drift, and operator error are realistic threats. Controls therefore aim to make unsafe connectivity structurally difficult rather than relying only on administrator discipline.

## 5.1 Principal Threats

- Cross-tenant lateral movement caused by route leakage, shared-policy mistakes, or permissive defaults.

- Inter-zone bypass caused by direct platform routing, generic transit VRFs, or broad shared-services reachability.

- Management-plane compromise through workload-to-management connectivity.

- Uncontrolled public ingress or Internet egress.

- IPv6 or alternate path bypass when only IPv4 is tested.

- Automation identities with excessive privileges or shared credentials.

- Configuration drift outside the infrastructure-as-code workflow.

- Failure-state bypass caused by security controls failing open.

- Platform portability claims that silently downgrade security on a less capable platform.

[Previous chapter](4-core-conceptual-model.md) · [Chapter index](README.md) · [Next chapter](09-part-ii-reference-architecture.md)
