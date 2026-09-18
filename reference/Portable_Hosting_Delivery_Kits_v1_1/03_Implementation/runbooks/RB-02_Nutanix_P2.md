# RB-02 — Nutanix native platform commissioning

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Nutanix platform owner. Assign an actual owner before use.

**Baseline:** RA §16,22; VND §3; VC §2; K05. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

RB-00 and applicable G1; selected AOS/AHV/Prism/Flow tuple, hardware, support, licenses and native installer procedure.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-02-01 — Confirm native support

**Action:** Resolve cluster, manager, Flow, provider/API and hardware compatibility and enabled feature scope.

**Expected observation:** Every needed operation has support evidence or an accepted alternative.

**Stop / preserve:** A v2 resource name or provider availability is not full support.

**Evidence:** Tuple/operation-coverage record.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-02-02 — Install under native ownership

**Action:** Execute the approved vendor installation/lifecycle artifact with the protected management path.

**Expected observation:** Native cluster and control services are healthy at the recorded versions.

**Stop / preserve:** Use supported recovery on failure; never create a competing configuration owner.

**Evidence:** Installer and native task receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-02-03 — Establish eligible pools

**Action:** Configure approved host/zone/co-residency eligibility, storage/controller membership, templates and protection integration.

**Expected observation:** Placement and restart constraints cover actual shared dependencies.

**Stop / preserve:** Do not treat separate guest networks as physical isolation.

**Evidence:** Placement/storage/management as-built.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-02-04 — Commission virtual network capability

**Action:** Prepare platform transport and isolated external handoff capacity; verify supported gateway/no-NAT/NAT choice and policy ownership.

**Expected observation:** Independent domain routing and baseline controls precede endpoints.

**Stop / preserve:** Shared connected external paths remain ineligible until isolation is proven.

**Evidence:** Native handoff, route and policy observations.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-02-05 — Create authorized disposable fixture

**Action:** Under restricted test permission, realize the WD logical roles with site allocations and current mandatory policy.

**Expected observation:** Fixture ownership is stable; partial resources remain denied.

**Stop / preserve:** Do not use documentation addresses as actual allocations or introduce production data.

**Evidence:** Fixture inventory and build receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-02-06 — Qualify and hand over

**Action:** Observe relevant W14/CT outcomes, failure and restore; record actual resource create/update/adopt/delete handling.

**Expected observation:** Accepted capability scope and limitations available for G2.

**Stop / preserve:** Unrun or failed mandatory observation remains open.

**Evidence:** Qualification report, native IDs and G2 scope decision.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
