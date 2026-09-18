# 13. Physical Fabric

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
![Image: image4.png](../../assets/diagrams/5cacf3e0d64939d48ccd.png)

Figure 5. Stable physical fabric with platform and security-edge attachments.

The recommended network foundation is a routed L3 Clos fabric using ECMP, with EVPN/VXLAN employed where overlay transport or physical-service attachment requires it. The design goal is to prevent tenant scale from becoming switch-control-plane scale.


<a id="source-table-137"></a>

| Physical Fabric Responsibility | Default |
| --- | --- |
| Resilient IP underlay | YES |
| ECMP path diversity | YES |
| EVPN/VXLAN transport where required | YES |
| HCI / platform attachment | YES |
| Security-edge attachment | YES |
| Per-tenant application policy | NO |
| Per-WSD firewall policy | NO |
| Routine per-tenant VRF provisioning | NO |
| Workload lifecycle | NO |


<a id="source-table-138"></a>

| FAB-001 | Normal creation, modification, and deletion of tenants, WSDs, workload networks, and workload security policies SHALL NOT require physical fabric changes. |
| --- | --- |


<a id="source-table-139"></a>

| FAB-002 | A physical VRF SHALL be created only when the physical fabric itself must provide L3 routing for a legitimate routing/security domain. |
| --- | --- |


<a id="source-table-140"></a>

| FAB-003 | Function names such as backup, migration, platform, ZIP, or generic transit SHALL NOT by themselves justify a VRF. |
| --- | --- |

## 13.1 Acceptable Reasons for a Physical VRF

- Physical servers or appliances that must route within the same Security Domain Instance.

- A physical external/partner domain that must be kept separate from other routing authorities.

- A dedicated high-assurance domain whose architecture requires physical-fabric routing separation.

- A site/service architecture in which the fabric, rather than a platform overlay, is the authorized L3 realization.

[Previous chapter](12-management-and-out-of-band-architecture.md) · [Chapter index](README.md) · [Next chapter](14-platform-overlay-architecture.md)
