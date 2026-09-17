# RB-01 — P0–P1 bootstrap and physical foundation

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Foundation deployment lead. Assign an actual owner before use.

**Baseline:** RA §§3–6,21; PROV §2; ET §§2–3. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

RB-00 accepted; actual equipment, facility interfaces, addresses, routing design, configuration method and custody resolved.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-01-01 — Verify staged inventory

**Action:** Reconcile received hardware/software/entitlements against the accepted BOM and trusted source.

**Expected observation:** Components and firmware/driver tuple are accounted for.

**Stop / preserve:** Quarantine mismatched or unverified items; retain custody evidence.

**Evidence:** Inventory and compatibility receipt.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-01-02 — Accept physical installation

**Action:** Qualified personnel complete approved manufacturer/facility installation and record links, racks, power and failure groups.

**Expected observation:** Physical topology matches the released design.

**Stop / preserve:** Do not improvise electrical, lifting or restricted facility procedures.

**Evidence:** Facility installation and port/cable receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-01-03 — Establish bootstrap trust

**Action:** Use the supported restricted console/OOB process and controlled temporary identity; provide accepted minimum time/name/trust.

**Expected observation:** Privileged access is restricted and recoverable without tenant routing.

**Stop / preserve:** Do not enable broad workload management reachability to finish bootstrap.

**Evidence:** Bootstrap access, dependency and temporary-grant record.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-01-04 — Commission transport

**Action:** Apply the accepted native configuration through the authoritative tool; verify neighbors, allowed routes, MTU and attachment membership.

**Expected observation:** Observed underlay/fabric matches the selected design.

**Stop / preserve:** Unexpected route import or bypass: stop, isolate affected scope and follow supported recovery.

**Evidence:** Native configuration, routing and path observations.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-01-05 — Verify the failure boundary

**Action:** Run only approved link/management fault observations with restoration procedures.

**Expected observation:** Required access and enforcement survive as specified; interruption measured.

**Stop / preserve:** No unapproved fault injection; do not treat denied traffic as proof of availability.

**Evidence:** Fault scope, observations and restoration receipt.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-01-06 — Release G1 scope

**Action:** Handover actual configuration, inventory, recovery copy, telemetry, capacity and limitations.

**Expected observation:** Dependent platform work consumes accepted foundation capacity.

**Stop / preserve:** Open mandatory foundation issue blocks affected consumption.

**Evidence:** G1 decision and P1 handoff.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
