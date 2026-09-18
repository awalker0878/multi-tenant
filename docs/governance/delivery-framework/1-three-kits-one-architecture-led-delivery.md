# 1. Three kits, one architecture-led delivery

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d8c2790ff7bb408283a9156a369cc6c4394131e7d44bfd130bfa27e7d82b5783 -->
<!-- SOURCE-BLOCK DEL:17 BEGIN -->

<a id="DEL_01"></a>

<!-- SOURCE-BLOCK DEL:17 END -->

<!-- SOURCE-BLOCK DEL:18 BEGIN -->

The architecture defines what exists and why. Engineering makes it buildable. Implementation provides actual observations and an accountable operating handoff.

<!-- SOURCE-BLOCK DEL:18 END -->

<!-- SOURCE-BLOCK DEL:19 BEGIN -->

Design basis and related records: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)  •  [AK §1](../../architecture/delivery-guide/1-architecture-work-plan-and-definition-of-done.md#AK_01)  •  [EK §1](../../engineering/delivery-guide/1-engineering-work-plan-and-release-boundary.md#EK_01)  •  [IK §1](../../implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md#IK_01)

<!-- SOURCE-BLOCK DEL:19 END -->

<!-- SOURCE-BLOCK DEL:20 BEGIN -->


<a id="source-table-20"></a>

| Work | Primary question | Current developed companion |
| --- | --- | --- |
| Architecture | What service is offered, which boundaries and sharing are accepted, and what must survive or recover? | SDP develops service envelopes, alternatives, dependencies and the engineering decision contract. |
| Engineering | Which exact components, routes, policies, pools, supported mechanisms and failure budgets realize the design? | NBD develops network/boundary schedules; PBS develops native platform builds and shared handoffs. |
| Implementation | How is the accepted design commissioned, qualified, activated, maintained and retired? | QCP develops campaign observations; OPS develops dependency loss, recovery, transition and operating acceptance. |

<!-- SOURCE-BLOCK DEL:20 END -->

<!-- SOURCE-BLOCK DEL:21 BEGIN -->

<!-- SOURCE-BLOCK DEL:21 END -->

<!-- SOURCE-BLOCK DEL:22 BEGIN -->

Start with the service and physical/logical design, then choose native realizations and provisioning packages. Terraform manages supported infrastructure operations alongside native installers, lifecycle and service tooling. No custom controller, schema registry or new application architecture is required by this release.

<!-- SOURCE-BLOCK DEL:22 END -->

<!-- SOURCE-BLOCK DEL:23 BEGIN -->

Use one selected stack and the necessary shared foundations for first qualification. Repeat the required service outcomes on a second stack for deployment comparison, then rehearse representative data/image recovery for the separate portability claim. A simultaneous multi-stack service is an explicit additional design.

<!-- SOURCE-BLOCK DEL:23 END -->

<!-- SOURCE-BLOCK DEL:24 BEGIN -->

This is a reusable reference and delivery-development package. It does not contain actual site allocations, native deployment modules, executed qualification evidence or authority to operate.

<!-- SOURCE-BLOCK DEL:24 END -->

<!-- SOURCE-BLOCK DEL:25 BEGIN -->

Continue with: [SDP §1](../../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md#SDP_01)  •  [PBS §1](../../engineering/platform-build/1-choose-the-platform-boundary-and-configuration-owner.md#PBS_01)

<!-- SOURCE-BLOCK DEL:25 END -->

<!-- SOURCE-BLOCK DEL:26 BEGIN -->

<!-- SOURCE-BLOCK DEL:26 END -->

[Chapter index](README.md) · [Next chapter](2-preserve-stable-deliverables-and-explicit-handoffs.md)
