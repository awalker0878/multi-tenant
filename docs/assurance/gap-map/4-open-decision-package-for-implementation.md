# 4. Open decision package for implementation

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/01_Gap_Map_and_Decision_Register_v1_4.docx) · [Chapter index](README.md)

> **Source:** GM — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 26dbaac8c13797b58ca5d057f76df8b3da63ec3f4b336036f18f5c6902512207 -->
<a id="__RefHeading___Toc1265_342027687"></a>
<a id="GM_s_004"></a>

Parent architecture: [RA §29](../../architecture/reference/29-architecture-decisions-and-alternatives.md#RA_s_029)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

The parent’s AD-01 through AD-15 choices remain proposed architectural decisions. The following implementation decisions instantiate those choices without silently changing them. Each record needs an actual owner, selected option, source/support evidence, affected interfaces/resources, approval and review trigger. The supplied site-decisions register leaves unknown selections explicitly open.


<a id="source-table-250"></a>

| Decision ID / question | Reference default or method | Required site outcome / related gaps |
| --- | --- | --- |
| D01 · site and cell topology | Bounded cells and explicit shared failure dependencies. | Actual inventories, pools and fault groups; G02/G27. |
| D02 · zone and co-residency | Retain zone-specific baseline; disclose controller/storage/mgmt sharing. | Approved authority-level sharing matrix; G10/G30. |
| D03 · fabric and multihoming | Routed large-site design; native overlays independent. | Supported underlay, peers, MTU and attachment design; G04/G05. |
| D04 · domain-to-ZIP handoff | Isolated routing identity per domain; shared paths require proof. | Native attachment allocation and enforceable forward/return paths; G03/G06. |
| D05 · vendor implementation tuples | Nutanix, VMware/NSX or selected OpenStack realization with explicit alternatives. | Current hardware/software/licence/API/provider and operation support; G12–G14/G18/G32. |
| D06 · management and bootstrap | Independent recovery access and scoped administrative domains. | Actual surviving OOB/trust/name/time/key dependencies; G09/G17/G23. |
| D07 · offered protocols/services | Declare supported address families and exact consumption profiles. | Complete family-specific service paths, including DNS behaviour; G07/G08/G22. |
| D08 · storage and recovery | Owned data/copies and isolated restore; fencing before recovery promotion. | Capture method, consistency, keys, retention and approved targets; G24–G26. |
| D09 · delivery tooling and ownership | P0–P6 with one authoritative resource writer and bounded handoffs. | Supported tools, operation coverage, failed-run recovery and adoption; G16/G18–G21. |
| D10 · service envelope | Measured survivor capacity and accountable service parameters. | Actual performance, SLO/RTO/RPO, limits, reserve and cadence; G27/G28. |
| D11 · qualification and operation | First-stack then second-stack portability; actual evidence and responsible authority. | Assertion/applicability plan, executed results, owners and authorization; G29–G31. |
| D12 · extensions | Excluded until a separate complete realization is accepted. | Scope and qualification for bare metal/containers/special patterns; G33. |

A vendor or site choice that cannot meet the selected reference outcome is not filled in as “equivalent” without analysis. Either choose another qualified realization, exclude the capability, or submit an explicit parent architecture variation. A missing service target is likewise an open service decision, not a reason to advertise a default number.

Related engineering: [Site design deliverables](../site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)  •  [Service parameter records](../site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [Vendor confirmation records](../../engineering/platform-realizations/7-implementation-tuple-and-decision-package.md#VND_s_007)

[Previous chapter](3-detailed-gap-register-and-treatment.md) · [Chapter index](README.md) · [Next chapter](5-completion-and-ongoing-closure.md)
