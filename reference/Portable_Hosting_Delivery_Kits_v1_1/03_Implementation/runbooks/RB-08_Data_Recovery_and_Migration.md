# RB-08 — Data recovery, platform exit and controlled failback

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Data and recovery authorities. Assign an actual owner before use.

**Baseline:** RA §§14,27; SVC §6; WD §§10,12–13. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

Actual scope, accepted data/copy/key inventory, target design, qualified method, objective boundaries and separately approved exercise/change.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-08-01 — Declare scope and writer authority

**Action:** Identify failed/source/target systems, consistency requirements and permitted recovery action. Fence ambiguous writers by the accepted mechanism.

**Expected observation:** One authorized write authority and protected evidence.

**Stop / preserve:** Do not promote a second writer while ownership is unresolved.

**Evidence:** Fencing and recovery authority record.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-08-02 — Restore minimum dependencies

**Action:** Recover approved administration, trust, name/time, keys/catalogue and source/configuration access.

**Expected observation:** Recovery path does not depend solely on the failed platform.

**Stop / preserve:** No plaintext, replacement-key or unrestricted privileged fallback.

**Evidence:** Dependency health and custody receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-08-03 — Prepare isolated target

**Action:** Establish eligible compute/data/network boundaries and required services under deny.

**Expected observation:** Target supports required image/device/data/identity semantics.

**Stop / preserve:** Unsupported conversion or co-residency blocks target use.

**Evidence:** Target as-built and compatibility checks.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-08-04 — Transfer or restore consistent state

**Action:** Use the approved platform/data tool through bounded authorized access; preserve copy lineage and measure actual data point.

**Expected observation:** Useful consistent data is available and attributable.

**Stop / preserve:** A completed job is not evidence of useful recovered data.

**Evidence:** Transfer/restore logs and integrity/consistency markers.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-08-05 — Verify and reconnect

**Action:** Check application-owner data acceptance, required security/services and recovery timing before approved DNS/exposure cutover.

**Expected observation:** Current authority accepts the defined recovered service.

**Stop / preserve:** Failed verification keeps target isolated.

**Evidence:** Measured RTO/RPO scope and activation record.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-08-06 — Fail back or retire source

**Action:** Plan reverse synchronization after new writes; remove temporary routes/grants and reconcile retained copies.

**Expected observation:** No stale writer, uncontrolled transition path or destroyed held key.

**Stop / preserve:** Starting an old VM is not automatically safe rollback.

**Evidence:** Failback/source-retirement and retained-data receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
