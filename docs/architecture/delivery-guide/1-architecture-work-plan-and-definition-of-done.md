# 1. Architecture work plan and definition of done

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<!-- SOURCE-BLOCK AK:17 BEGIN -->

<a id="AK_01"></a>

<!-- SOURCE-BLOCK AK:17 END -->

<!-- SOURCE-BLOCK AK:18 BEGIN -->

The architect owns the coherence of the whole hosting service, not a Terraform repository or a custom application. The design must explain what exists, how it connects, which parties control it and what happens during change or failure.

<!-- SOURCE-BLOCK AK:18 END -->

<!-- SOURCE-BLOCK AK:19 BEGIN -->

Baseline and related records: [RA §1](../reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §3](../reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [AT §1](../../templates/hld/1-mandate-and-service-envelope.md#AT_01)

<!-- SOURCE-BLOCK AK:19 END -->

<!-- SOURCE-BLOCK AK:20 BEGIN -->


<a id="source-table-20"></a>

| Work | Input | Output / review |
| --- | --- | --- |
| Frame the service | Demand, beneficiaries, information envelope, current estate and constraints. | AK-01 with explicit exclusions and stakeholders. |
| Select obligations | Reference requirements, applicable source editions, service targets and inherited controls. | AK-02 with owner, applicability and verification. |
| Develop linked views | Physical/logical components, boundaries, resources, flows and dependencies. | AK-03 with IDs that persist into engineering. |
| Resolve decisions | Viable options, security/resilience consequences, costs and exit effects. | AK-04–07; proposed versus actually adopted choices distinguished. |
| Review and release | Cross-discipline walkthrough, unresolved risks and necessary authority. | AK-08; accepted handoff or specific blocking gaps. |

<!-- SOURCE-BLOCK AK:20 END -->

<!-- SOURCE-BLOCK AK:21 BEGIN -->

<!-- SOURCE-BLOCK AK:21 END -->

<!-- SOURCE-BLOCK AK:22 BEGIN -->

## Definition of done

<!-- SOURCE-BLOCK AK:22 END -->

<!-- SOURCE-BLOCK AK:23 BEGIN -->

A reviewer can trace an allowed flow and its reply, explain why an alternative path is blocked, locate the management and storage boundaries, understand the sharing decision, and identify the exact engineering records still required. Unknown site values are assigned—not hidden as product defaults.

<!-- SOURCE-BLOCK AK:23 END -->

<!-- SOURCE-BLOCK AK:24 BEGIN -->

Do not accept a drawing that is only a list of products. Do not call a collection of API object definitions the infrastructure architecture.

<!-- SOURCE-BLOCK AK:24 END -->

<!-- SOURCE-BLOCK AK:25 BEGIN -->

<!-- SOURCE-BLOCK AK:25 END -->

[Chapter index](README.md) · [Next chapter](2-service-requirements-and-applicability.md)
