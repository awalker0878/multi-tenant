# 6. Capacity and test-resource accounting

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/Worked_Delivery_Example.docx) · [Chapter index](README.md)

> **Source:** WDE — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: ae4ea65ea564fe848f214f5154ca4b67726eb6628d07a4b4f7714210e49ccd0d -->
<a id="EX_06"></a>

Reference demand and actual deliverable capacity are different quantities. The engineering workbook separates them.

Baseline and related records: [WD §11](../internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)  •  [QUAL §3](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [EK §6](../../engineering/delivery-guide/6-capacity-mtu-performance-and-failure-analysis.md#EK_06)


<a id="source-table-59"></a>

| Reference case | Derived guest demand | Limit of the calculation |
| --- | --- | --- |
| Four permanent endpoints | 8 vCPU, 16 GiB memory and 360 GiB virtual disks. | 4 × (2 vCPU, 4 GiB, 40 GiB boot), plus two 100 GiB data disks. |
| One sequential test probe | Peak 10 vCPU, 20 GiB memory and 400 GiB virtual disks. | One extra endpoint at the same small test size; not four simultaneous probes. |
| Four simultaneous test probes | 16 vCPU, 32 GiB memory and 520 GiB virtual disks. | Alternative test execution plan only; cannot count it as the sequential plan. |
| Provider infrastructure | Additional, not quantified by the four guest VMs. | Controllers, edge/services, protection, replicas, hypervisor overhead and required reserves must be included. |
| Surviving capacity | Accepted load plus increment must fit each remaining dimension after failure and reserve. | Memory, storage, edge throughput/sessions, routes, attachments and service/API limits cannot substitute for one another. |

## MTU example

For basic VXLAN carrying an untagged inner Ethernet frame, a 1450-byte workload IP packet adds 14 + 8 + 8 + 20 bytes for inner Ethernet, VXLAN, UDP and outer IPv4: 1500 bytes of outer IP packet. With outer IPv6, use 40 rather than 20: 1520 bytes. An inner VLAN tag adds another 4 bytes. Outer link framing and actual device MTU definitions are separate.

The workbook exposes these inputs and arithmetic. Geneve options, IPsec, nested tunnels and other headers need their actual byte budget. An illustrative fit does not establish that every active and surviving path supports the selected workload MTU.

[Previous chapter](5-commission-qualify-prepare-and-activate.md) · [Chapter index](README.md) · [Next chapter](7-observe-recover-and-retire-without-invented-results.md)
