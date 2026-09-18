# RB-03 — VMware/NSX native platform commissioning

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** VMware/NSX platform owners. Assign an actual owner before use.

**Baseline:** RA §17,22; VND §4; VC §3; KIT-TN-01. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

RB-00 and G1; actual ESXi/vCenter/NSX/provider/hardware/entitlement tuple, gateway modes and supported installation artifacts.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-03-01 — Confirm routing-mode compatibility

**Action:** Validate exact Tier-1/upstream context, parent Tier-0/VRF and HA mode against installed-release documentation and KIT-TN-01.

**Expected observation:** Selected modes and service functions are supported together.

**Stop / preserve:** Do not change a live parent mode merely to satisfy this checklist; require a separate impact-reviewed change.

**Evidence:** Gateway compatibility decision.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-03-02 — Commission compute/storage management

**Action:** Execute approved native vCenter/ESXi and storage installation, eligible pools, image/boot and management configuration.

**Expected observation:** Actual placements and data dependencies match the LLD.

**Stop / preserve:** Unsupported tuple or hidden shared management boundary blocks service acceptance.

**Evidence:** Platform installation and pool as-built.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-03-03 — Commission NSX transport and edge

**Action:** Establish approved managers, transport nodes/zones, Edge capacity, uplinks and isolated upstream contexts.

**Expected observation:** Actual distributed and centralized routing roles are identifiable.

**Stop / preserve:** No common unrestricted native route table substitutes for the security boundary.

**Evidence:** Transport/gateway/Edge configuration and path record.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-03-04 — Protect mandatory endpoint and edge policy

**Action:** Apply provider-owned groups, policy hierarchy and separately authorized ZIP relationships before workload connection.

**Expected observation:** Same-host and cross-host controls cannot be widened by tenant mutation.

**Stop / preserve:** Unexpected permissive default or override path keeps resources isolated.

**Evidence:** Effective policy and role observations.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-03-05 — Run restricted fixture and faults

**Action:** Build the accepted disposable domains/VMs/disks; observe native route propagation, return context, HA/restart and protection.

**Expected observation:** Observed outcomes support the offered service and actual failure scope.

**Stop / preserve:** No unsupported HA or live-migration promise; stop unsafe fault execution.

**Evidence:** Qualified test observations and recovery receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-03-06 — Release scoped capability

**Action:** Record vSphere/NSX ownership, provider lifecycle coverage, actual limits, limitations and evidence.

**Expected observation:** G2 considers a concrete service/tuple rather than product names.

**Stop / preserve:** Missing exact evidence prevents qualification.

**Evidence:** As-built/coverage and qualification decision.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
