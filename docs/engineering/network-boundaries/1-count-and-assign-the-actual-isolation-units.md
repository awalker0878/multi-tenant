# 1. Count and assign the actual isolation units

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<a id="NBD_01"></a>

A routing context, a logical ZIP relationship, an attachment and a physical appliance are different units. Count each before choosing a topology.

Design basis and related records: [WD §3](../../solutions/internal-protected-workload/3-component-and-dependency-schedule.md#WD14_S03)  •  [WD §4](../../solutions/internal-protected-workload/4-tenant-attachment-and-address-schedule.md#WD14_S04)  •  [NET §2](../fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [EK §3](../delivery-guide/3-addressing-routing-policy-and-attachment-schedules.md#EK_03)

The fixture contains D01O, D01R, D02O and D02R. Four domain-to-edge handoffs attach these domains to EC-01 or EC-02. Two further service handoffs attach EC-01 to SE-01 and EC-02 to SE-02. EC and SE identify logical ownership/forwarding roles in the worked design, not a purchase quantity or a claim that one firewall implements every role.


<a id="source-table-20"></a>

| Unit | Fixture identity / count | Engineering owner and restriction |
| --- | --- | --- |
| Domain handoff | A01O, A01R, A02O, A02R: four. | Platform and edge owners agree both endpoints; no unrelated connected context. |
| Service handoff | SH-01, SH-02: two. | Edge and shared-service owners agree source scope, service route and reply. |
| Tenant edge context | EC-01 and EC-02: two logical contexts. | Independent routing/policy authority; physical sharing and HA are separately qualified. |
| Service-side context | SE-01 and SE-02: two logical return-path scopes. | Only named service delivery; no unapproved transit between tenant contexts. |
| Physical capacity | Not determined by these counts. | Add actual interface members, HA/synchronization, hosts, licences and reserved spare slots. |

Allocate attachment slots from commissioned pools with an owner, capacity class, lifecycle and quarantine/reuse condition. A slot is unavailable while an old route, neighbour entry, policy association or native task can still refer to its previous owner. Pool expansion is a foundation change, not an excuse to share a connected network without qualification.

Release criterion: every logical unit resolves to its native objects and physical dependencies, with one configuration writer and an accepted boundary owner.

Continue with: [PBS §8](../platform-build/8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)  •  [NBD §6](6-issue-an-interface-control-and-handoff-record.md#NBD_06)

[Chapter index](README.md) · [Next chapter](2-walk-f14-01-through-the-forward-and-reply-routes.md)
