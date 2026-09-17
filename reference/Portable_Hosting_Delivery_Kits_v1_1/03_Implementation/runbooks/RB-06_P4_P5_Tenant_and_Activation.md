# RB-06 — P4–P5 qualification fixture, tenant build and activation

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Tenant deployment and acceptance owners. Assign an actual owner before use.

**Baseline:** RA §23; WD §§9–11,13; IK §§6–7. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

RB-00; resolve whether restricted qualification or production. Production requires qualified capacity and applicable initial G4 plus operating authority.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-06-01 — Choose the authorized path

**Action:** Record restricted fixture permission or production prerequisites, exact service envelope and tenant owner.

**Expected observation:** No production permission inferred from test authorization.

**Stop / preserve:** Missing actual authorization stops the affected operation.

**Evidence:** Scope-specific gate/test decision.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-06-02 — Reserve eligible resources

**Action:** Allocate authoritative addresses, capacity, storage and attachment/security slots; establish tenant/domain scope.

**Expected observation:** One owned reservation per resource; actual allocation recorded.

**Stop / preserve:** No guessed values or use of excluded capacity.

**Evidence:** Reservations and native scope identities.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-06-03 — Build denied topology

**Action:** Create owned networks, gateways and baseline policy; coordinate paired edge routes/flows under the edge owner.

**Expected observation:** No endpoint is exposed before mandatory enforcement.

**Stop / preserve:** Unverified partial state remains disconnected/quarantined.

**Evidence:** Native topology and policy receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-06-04 — Create protected resources

**Action:** Instantiate approved images/VMs/disks in eligible pools, then names, service identities, telemetry and protection.

**Expected observation:** Actual attachments and client/admin boundaries match the LLD.

**Stop / preserve:** Do not weaken placement or data custody to complete the request.

**Evidence:** As-built resource/protection record.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-06-05 — Observe applicable outcomes

**Action:** Run scoped healthy-control, permitted/denied, resource/role, family and recovery observations.

**Expected observation:** Actual results and artifacts recorded separately from expected outcomes.

**Stop / preserve:** Unknown/failed mandatory results remain open, not passes.

**Evidence:** IT test records and evidence index.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-06-06 — Complete initial readiness and activate

**Action:** For production, verify G0/G1/G2/current tests, applicable G4 initial and valid operating authority; execute the approved exposure change and verify it.

**Expected observation:** Only the accepted service scope becomes active.

**Stop / preserve:** Failed live verification withdraws exposure without destroying data.

**Evidence:** G3 decision, activation/post-check and operations confirmation.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-06-07 — Close or retain the fixture

**Action:** Retire disposable test resources and reconcile reservations or formally accept the authorized continuing scope.

**Expected observation:** No stale test permissions or orphan resource.

**Stop / preserve:** Hold required evidence/data; do not blind-destroy shared resources.

**Evidence:** Residual scan and scope closure.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
