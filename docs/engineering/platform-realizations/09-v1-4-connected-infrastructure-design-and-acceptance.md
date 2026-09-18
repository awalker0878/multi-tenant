# v1.4 — Connected infrastructure design and acceptance

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:131 BEGIN -->

<a id="__RefHeading___Toc7279_1692646980"></a>
<a id="V14_VND_REVISION"></a>

<!-- SOURCE-BLOCK VND:131 END -->

<!-- SOURCE-BLOCK VND:132 BEGIN -->

## Concrete schedules and protected network-policy ownership

<!-- SOURCE-BLOCK VND:132 END -->

<!-- SOURCE-BLOCK VND:133 BEGIN -->

The same WD resource and path identities are mapped to each native platform. For the base OpenStack realization, provider-owned roles retain mutation of mandatory network policy, port security, address pairs and external attachment. Tenant requests may use existing approved tooling; a bespoke controller is not required. Direct delegated editing is an extension requiring evidence that it cannot widen the mandatory envelope. Additive security-group allows are not a provider deny hierarchy. The complete fixture also reserves a temporary intra-domain probe; four single-endpoint domains alone cannot prove paired same-domain behavior.

<!-- SOURCE-BLOCK VND:133 END -->

<!-- SOURCE-BLOCK VND:134 BEGIN -->

Authoritative linked treatment: [WD — Worked Infrastructure Design, Build Schedules and Acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

<!-- SOURCE-BLOCK VND:134 END -->

<!-- SOURCE-BLOCK VND:135 BEGIN -->

Read this clarification with the original chapter. It does not create an exemption to an adopted requirement, waive a mandatory control, select an unknown site value or report a live test as passed.

<!-- SOURCE-BLOCK VND:135 END -->

<!-- SOURCE-BLOCK VND:136 BEGIN -->


<a id="source-table-136"></a>

| Policy model | Base service choice | Extension condition |
| --- | --- | --- |
| Provider-managed baseline | Only approved provider identities mutate protected network policy and attachment settings. | Actual API/native roles and alternate creation paths tested. |
| Bounded tenant delegation | Not part of the unqualified base offer. | A supported effective-policy envelope must survive additive permits, new ports/NICs, address pairs and alternate router/external paths. |

<!-- SOURCE-BLOCK VND:136 END -->

<!-- SOURCE-BLOCK VND:137 BEGIN -->

<!-- SOURCE-BLOCK VND:137 END -->

[Previous chapter](08-references-parent-basis-and-external-context.md) · [Chapter index](README.md)
