# 2. Choose sharing at each infrastructure layer

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx) · [Chapter index](README.md)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->
<!-- SOURCE-BLOCK SDP:25 BEGIN -->

<a id="SDP_02"></a>

<!-- SOURCE-BLOCK SDP:25 END -->

<!-- SOURCE-BLOCK SDP:26 BEGIN -->

The sharing decision changes security exposure, eligible capacity, operating authority and the failure model simultaneously.

<!-- SOURCE-BLOCK SDP:26 END -->

<!-- SOURCE-BLOCK SDP:27 BEGIN -->

Design basis and related records: [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [AK §4](../../architecture/delivery-guide/4-security-management-and-co-residency-decisions.md#AK_04)

<!-- SOURCE-BLOCK SDP:27 END -->

<!-- SOURCE-BLOCK SDP:28 BEGIN -->

Retain the parent’s zone-aware host-pool baseline. Do not infer that independent domains may share a host merely because both carry an RZ label. Where an alternative is proposed, evaluate the actual host, HCI controllers, storage, management and recovery placement together. Record the variation rather than silently relaxing the baseline.

<!-- SOURCE-BLOCK SDP:28 END -->

<!-- SOURCE-BLOCK SDP:29 BEGIN -->


<a id="source-table-29"></a>

| Design alternative | What remains shared | Consequence to evaluate |
| --- | --- | --- |
| Compatible-domain pooled capacity | Only layers permitted by the adopted sharing decision. Routing and policy authority remain distinct. | Higher utilization may be possible, but host/controller compromise and correlated failure remain assessed dependencies. |
| Dedicated workload host pool | Potentially storage, edge, management, backup and key services. | Host dedication does not create an independently administered service. Reserve replacement and evacuation capacity in eligible pools. |
| Dedicated wider service scope | Only specifically accepted external dependencies. | More independent capacity, management and recovery may be needed; define exactly what is dedicated and why. |

<!-- SOURCE-BLOCK SDP:29 END -->

<!-- SOURCE-BLOCK SDP:30 BEGIN -->

<!-- SOURCE-BLOCK SDP:30 END -->

<!-- SOURCE-BLOCK SDP:31 BEGIN -->

## Worked decision boundary

<!-- SOURCE-BLOCK SDP:31 END -->

<!-- SOURCE-BLOCK SDP:32 BEGIN -->

Suppose a workload requires dedicated hosts but accepts the provider’s separately controlled backup service. Record hosts as dedicated, backup infrastructure as shared with isolated authority, and retained-copy/key controls as mandatory. A later host failure cannot move the VM into an unrelated shared pool simply because a scheduler finds free memory. If eligible capacity is exhausted, the declared service degrades or uses another already approved pool.

<!-- SOURCE-BLOCK SDP:32 END -->

<!-- SOURCE-BLOCK SDP:33 BEGIN -->

The engineering handoff names the rule the scheduler must enforce, the components it does not isolate, the reserve needed during maintenance, and the test demonstrating restart and restore eligibility. Do not represent this as a single “dedicated=true” checkbox.

<!-- SOURCE-BLOCK SDP:33 END -->

<!-- SOURCE-BLOCK SDP:34 BEGIN -->

Continue with: [PBS §1](../../engineering/platform-build/1-choose-the-platform-boundary-and-configuration-owner.md#PBS_01)  •  [QCP §4](../../assurance/qualification-campaign/4-observe-identity-storage-and-protocol-completeness.md#QCP_04)

<!-- SOURCE-BLOCK SDP:34 END -->

<!-- SOURCE-BLOCK SDP:35 BEGIN -->

<!-- SOURCE-BLOCK SDP:35 END -->

[Previous chapter](1-define-the-offered-service-before-choosing-the-build.md) · [Chapter index](README.md) · [Next chapter](3-develop-a-boundary-architecture-decision.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0008 — Preserve zone-aware host placement and disclose every shared layer](../../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)

<!-- END GENERATED DECISION LINKS -->
