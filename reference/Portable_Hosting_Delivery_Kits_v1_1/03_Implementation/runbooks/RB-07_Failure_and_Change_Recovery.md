# RB-07 — Interrupted execution, adoption and controlled change

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Current authoritative resource owner. Assign an actual owner before use.

**Baseline:** RA §25; PROV §§5–6; WD §10. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

Approved recovery/change scope; native task visibility; known custody; read access to current state and incident constraints.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-07-01 — Stabilize ownership

**Action:** Pause competing changes and establish the actual writer, accepted tasks and incident restrictions.

**Expected observation:** No second executor makes assumptions about task cancellation.

**Stop / preserve:** Do not force-unlock until writer cessation is established by the approved recovery procedure.

**Evidence:** Task/writer/lock timeline.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-07-02 — Discover actual effects

**Action:** Compare native resources, addressing, routes, data and state against the last confirmed step.

**Expected observation:** Unknown outcomes become explicit owned findings.

**Stop / preserve:** Do not replay create blindly or infer failure from a lost response.

**Evidence:** Native IDs, task results and semantic difference.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-07-03 — Choose safe repair

**Action:** Owner approves resume, supported rollback, forward repair or isolated operator intervention with data effects.

**Expected observation:** Shared resources and newly written/held data are preserved.

**Stop / preserve:** No generic compensation may destroy required data.

**Evidence:** Recovery decision and bounded action plan.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-07-04 — Revalidate change basis

**Action:** Replan affected scope when input, policy, state or authority changed; reconcile supported brownfield ownership/import.

**Expected observation:** No stale plan or dual controller ownership.

**Stop / preserve:** Import alone is neither compliance nor permission for replacement.

**Evidence:** Fresh plan and ownership handoff.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-07-05 — Execute and observe

**Action:** Run approved scoped repair; retain containment until its authority releases it; verify impacted paths/data.

**Expected observation:** Actual desired and realized state converges with supporting evidence.

**Stop / preserve:** Unexpected effects stop further changes and trigger escalation.

**Evidence:** Repair/task receipts and retests.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-07-06 — Close and improve

**Action:** Update as-built, source, defects, reservations, custody and runbook lessons.

**Expected observation:** Unresolved effects remain visible and owned.

**Stop / preserve:** Do not rewrite historical approval or hide retained exceptions.

**Evidence:** Incident/change closure and revised records.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
