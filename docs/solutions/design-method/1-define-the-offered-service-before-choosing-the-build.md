# 1. Define the offered service before choosing the build

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx) · [Chapter index](README.md)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->
<a id="SDP_01"></a>

An offer is a bounded combination of resources, connectivity, operating responsibility and recoverability—not the name of a hypervisor.

Design basis and related records: [RA §2](../../architecture/reference/2-design-drivers-and-selected-reference-pattern.md#RA_s_002)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [AK §2](../../architecture/delivery-guide/2-service-requirements-and-applicability.md#AK_02)

Develop the initial offer around an internal VM environment with independent tenant OZ/RZ domains, declared shared-service consumption and no implicit public access. Describe the smallest unit that can be accepted: the WSD, its networks and data, the provider dependencies, and the agreed operating boundary. The same description becomes the input to each vendor realization.


<a id="source-table-19"></a>

| Offer decision | Proposed internal baseline | Explicit additional decision |
| --- | --- | --- |
| Resources | Eligible VM and storage classes; capacity is allocated from accepted pools. | Accelerators, unusual virtual devices or bare-metal attachment require a separate service design. |
| Connectivity | Named intra-domain and ZIP-mediated inter-domain flows; scoped service endpoints. | Public ingress, partner access or Internet egress requires its own boundary and operational acceptance. |
| Continuity | A named local failure model and protection/restore method. | Site recovery is offered only with an eligible target, independent dependencies and measured recovery evidence. |
| Operations | Named infrastructure, guest, application and data owners. | Managed guest services change responsibility only when explicitly agreed. |

For every offered item record a measurement boundary and an exclusion. “Resilient” must identify the failed resources and the service that continues. A security availability-impact label cannot supply an uptime target. A backup schedule cannot supply an RPO until its recoverable consistency point and failure behaviour are understood.

Output: a proposed service envelope and explicit exclusions. No hardware order, provider selection or production activation follows solely from this record.

Continue with: [SDP §5](5-make-capacity-on-demand-and-exit-economically-explainable.md#SDP_05)  •  [AT §1](../../templates/hld/1-mandate-and-service-envelope.md#AT_01)

[Chapter index](README.md) · [Next chapter](2-choose-sharing-at-each-infrastructure-layer.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0019 — Separate information impacts from service-level and recovery promises](../../adr/0019-separate-information-impacts-from-service-level-and-recovery-promises.md)
- [ADR-0022 — Treat public access and egress as explicit service extensions](../../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<!-- END GENERATED DECISION LINKS -->
