# 2. Preserve stable deliverables and explicit handoffs

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d8c2790ff7bb408283a9156a369cc6c4394131e7d44bfd130bfa27e7d82b5783 -->
<a id="DEL_02"></a>

The 27 AK/EK/IK output IDs and 194 inherited requirement records are not renumbered. New development records provide detail and navigation, not replacement requirements.

Design basis and related records: [AK §8](../../architecture/delivery-guide/8-engineering-handoff-and-change-impact.md#AK_08)  •  [EK §8](../../engineering/delivery-guide/8-build-test-and-implementation-handoff.md#EK_08)  •  [IK §1](../../implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md#IK_01)


<a id="source-table-30"></a>

| Handoff | Sender supplies | Receiver verifies |
| --- | --- | --- |
| Architecture → engineering | Service envelope, linked views, accepted sharing/boundary decisions, obligations and unresolved scope. | No contradiction or missing decision affects the intended build; each delegated engineering choice has a bounded outcome. |
| Engineering → implementation | Actual LLD, native mapping, supported tuple, configuration artifacts, interface receipts, MOP and observation plan. | No guessed address, competing writer, unsafe replacement or unsupported required operation. |
| Implementation → operations | As-built identities, actual tests, supported limits, current protection/recovery and retained obligations. | The service is supportable and recoverable; initial readiness existed before production activation. |

Carry a decision ID into its engineering schedule, native build package, assertion and evidence record. Diagrams use the same component/interface identities. Use the existing deliverables catalogue and role workbooks as working records; the new development register points to the supporting detail.

A handoff passes the minimum facts needed to consume a service: identities, permitted use, limits, support, acceptance revision and remaining restrictions. It does not transfer unrestricted credentials or change configuration ownership. Both producer and consumer must acknowledge the dependency.

Continue with: [SDP §6](../../solutions/design-method/6-release-the-architecture-as-an-accountable-engineering-contract.md#SDP_06)  •  [NBD §6](../../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md#NBD_06)  •  [PBS §8](../../engineering/platform-build/8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)  •  [PBS §9](../../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)

[Previous chapter](1-three-kits-one-architecture-led-delivery.md) · [Chapter index](README.md) · [Next chapter](3-apply-gate-dependencies-rather-than-numerical-order.md)
