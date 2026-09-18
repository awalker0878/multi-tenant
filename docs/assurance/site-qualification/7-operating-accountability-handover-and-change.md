# 7. Operating accountability, handover and change

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<a id="__RefHeading___Toc10045_1525915568"></a>
<a id="QUAL_s_007"></a>

Parent architecture: [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)


<a id="source-table-85"></a>

| Decision | Accountable role | Executing/consulted roles and evidence |
| --- | --- | --- |
| Adopt topology/variation | Architecture authority | Security, network, platform, storage and service owners; decision and affected interfaces. |
| Approve security boundary | Responsible security authority | Both adjacent domain authorities and edge owner; permitted flows and residual risks. |
| Accept cell/service capacity | Hosting service owner | Capacity, platform, network, edge and shared-service owners; measured service envelope. |
| Authorize tenant service activation | Tenant service acceptance owner under applicable authorization conditions | Platform, security, data and operations owners; current as-built and required checks. |
| Accept data retention/disposal | Data owner or designated disposition authority | Backup, storage, key and compliance owners; copy/hold/key evidence. |
| Contain incident / release containment | Designated incident authority | Affected service and security operations; scoped action, evidence and explicit release. |
| Execute shared foundation change | Assigned infrastructure change authority | Authoritative resource owners; compatibility, survivor capacity and recovery plan. |
| Issue formal system authorization | Designated authorizing official | Assessor and responsible owners; selected controls, evidence, residual risk and operating conditions. |

These are roles, not invented personnel assignments. The site must name actual teams and escalation contacts and map the reference decisions into its existing process. Separate approval and execution for high-impact changes as required by the adopted control set. One routine workload executor must not acquire unrestricted fabric, management, security-edge and tenant authority.

Handover covers as-built topology, component/owner inventory, offered class and limits, current support/patch state, monitoring questions and alerts, credential/custody arrangements, backup and key dependencies, recovery and failback runbooks, remaining gaps and accepted variations. The operator accepts this specific service, not merely receipt of a generic reference document.


<a id="source-table-89"></a>

| Operational question | Minimum attributable information | Action when missing |
| --- | --- | --- |
| Why is this flow allowed? | Tenant/domain identity, approved relationship, actual route/enforcement policy and responsible authority. | Restrict or investigate according to risk; do not infer permission from reachability. |
| Can the service survive the offered failure? | Current eligible survivor capacity and tested dependencies/runbooks. | Withdraw the unsupported promise or remediate under accountable ownership. |
| Who can change or destroy this resource/copy? | Actual native roles, tool ownership, retention and key custody. | Resolve authority before activation or disposal. |
| What changed outside approved configuration? | Before/after observed state, actor/time, service impact and current containment. | Preserve incident override, assign repair and reconcile source deliberately. |
| What is overdue or unsupported? | Asset/software support status, findings, remediation authority and accepted exception. | Escalate through adopted risk policy; do not invent universal deadlines. |

Related engineering: [Writer and containment handling](../../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md#PROV_s_005)  •  [Recovery/retirement accountability](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)

[Previous chapter](6-control-inheritance-assurance-and-organizational-interfaces.md) · [Chapter index](README.md) · [Next chapter](8-extensions-and-release-maintenance.md)
