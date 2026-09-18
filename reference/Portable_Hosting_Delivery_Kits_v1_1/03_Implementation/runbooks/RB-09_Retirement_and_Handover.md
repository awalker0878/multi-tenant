# RB-09 — Operational acceptance, retirement and retained obligations

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Service operations and data disposition owners. Assign an actual owner before use.

**Baseline:** RA §§26–28; QUAL §7; WD §§9–10,12. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

Actual inventory/ownership, consumers, holds, recovery requirements and approved disposition scope.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-09-01 — Accept actual operations scope

**Action:** Confirm owner/on-call/support, monitoring, accepted limits, patch/change process, custody and exercised recovery.

**Expected observation:** Initial readiness supports the production promise.

**Stop / preserve:** Missing actual owner or required restore evidence blocks initial acceptance.

**Evidence:** IT §6 and initial G4 decision.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-09-02 — Plan retirement and preserve obligations

**Action:** Identify dependent services/shared resources, held copies and keys; complete required export/backup before revoking required paths.

**Expected observation:** Every remaining obligation has an accountable owner.

**Stop / preserve:** Do not delete service access required to preserve held data.

**Evidence:** Disposition plan and copy lineage.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-09-03 — Withdraw live access

**Action:** Under the relevant owner, remove exposures, ordinary flows, names, routes and grants; confirm session handling.

**Expected observation:** No obsolete live connectivity/authority remains.

**Stop / preserve:** Do not remove another tenant’s shared domain/service.

**Evidence:** Native deletion and residual checks.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-09-04 — Remove eligible resources

**Action:** Delete only owned eligible workload/attachments; quarantine address reuse and preserve required history.

**Expected observation:** Actual native state and inventory agree.

**Stop / preserve:** Unknown asynchronous completion or reuse conflict remains blocked.

**Evidence:** As-built retirement and allocation release.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-09-05 — Sanitize approved data/media

**Action:** Use the approved media-appropriate process through qualified personnel; verify key/copy scope and held exceptions.

**Expected observation:** Reuse is supported by actual sanitization evidence.

**Stop / preserve:** Resource-record deletion is not proof of data destruction.

**Evidence:** Sanitization/retention receipt and verification.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-09-06 — Close and continue retained custody

**Action:** Retain tombstone, evidence, obligations, access/key custody and future review/disposal dates.

**Expected observation:** Live service retired; residual data remains explicitly controlled.

**Stop / preserve:** Do not mark total destruction while copies remain.

**Evidence:** Final service/data decision and continuing obligations.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
