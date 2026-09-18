# RB-05 — P3 security boundaries and shared services

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** Security-edge and shared-service owners. Assign an actual owner before use.

**Baseline:** RA §§8–13,22; SVC §§1–6; WD §§5–7. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

RB-00; approved EC/SE/ZIP and service topology; actual endpoints, paths, identities, protocols, HA and capacity.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-05-01 — Create owned security capacity

**Action:** Use the selected supported edge mechanism to instantiate isolated contexts/handoffs and separately protected management.

**Expected observation:** Only permitted domains and routes belong to each context.

**Stop / preserve:** Do not import unrelated tenant routes or expose admin interfaces on the consumption path.

**Evidence:** Context/interface and writer ownership receipt.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-05-02 — Establish forward/reply paths

**Action:** Configure accepted prefix and source policy, native gateway handoffs and service-side origin-specific replies.

**Expected observation:** No connected, neighbour, NAT or alternate default path bypasses enforcement.

**Stop / preserve:** Wrong or missing reply path remains unavailable rather than being masked by a broad route.

**Evidence:** Routing/FIB and stateful path observation.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-05-03 — Publish named service consumption

**Action:** Establish actual DNS/time/repository/log/identity endpoints, entitled operations and scoped initiators.

**Expected observation:** Selected complete protocols work, including applicable DNS TCP/UDP behaviour.

**Stop / preserve:** No broad provider subnet or administrative grant for a service binding.

**Evidence:** Endpoint/protocol and authorization tests.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-05-04 — Establish key and protection custody

**Action:** Identify actual key-service client, capture API, data mover, protected copies, catalogue and held-data obligations.

**Expected observation:** Tenant workloads do not inherit platform capture or key-destruction privileges.

**Stop / preserve:** Missing key/catalogue recovery or independent-copy protection blocks the promise.

**Evidence:** Role, copy lineage and recovery evidence.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-05-05 — Observe continuity and telemetry

**Action:** Test approved service/edge outages and restore paths; verify origin attribution, buffering and actual surviving capacity.

**Expected observation:** Security and service interruption both measured without fallback bypass.

**Stop / preserve:** No unsafe fault or reliance on untested caches.

**Evidence:** Fault/restore/telemetry and capacity report.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-05-06 — Accept service handoffs

**Action:** Publish actual endpoints, permitted operations, owners, versions, limits and dependencies to downstream packages.

**Expected observation:** P2/P3 offered capability is accepted before routine consumption.

**Stop / preserve:** Incomplete mandatory service blocks dependent activation.

**Evidence:** Service readiness and G2 contribution.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
