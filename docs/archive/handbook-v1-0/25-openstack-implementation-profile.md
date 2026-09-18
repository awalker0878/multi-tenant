# 25. OpenStack Implementation Profile

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
OpenStack maps the model to Keystone administrative tenancy and Neutron networking. Neutron networks/subnets, routers, security groups and provider/external networks can realize the portable constructs, subject to the capabilities enabled in the specific OpenStack distribution.


<a id="source-table-215"></a>

| Portable Concept | OpenStack Realization |
| --- | --- |
| Tenant Namespace | Keystone project |
| Security Domain Instance | Neutron router/address/routing context |
| Workload Network | Neutron network and subnet |
| Microsegmentation | Neutron security groups |
| External attachment | Router/provider network |
| Compute | Nova |
| Storage | Cinder |
| Metadata | Project/resource tags and orchestration metadata |


<a id="source-table-216"></a>

| OS-001 | Default OpenStack security-group behaviour SHALL be reviewed and normalized to the secure-by-default service baseline. |
| --- | --- |


<a id="source-table-217"></a>

| OS-002 | Provider networks and external-router capabilities SHALL remain provider controlled and SHALL not become unrestricted tenant escape paths. |
| --- | --- |

[Previous chapter](24-vmware-nsx-implementation-profile.md) · [Chapter index](README.md) · [Next chapter](26-bare-metal-and-future-platforms.md)
