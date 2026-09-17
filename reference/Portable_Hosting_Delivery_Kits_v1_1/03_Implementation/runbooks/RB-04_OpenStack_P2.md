# RB-04 — OpenStack native platform commissioning

**Status:** site-parameterized reference method; NOT EXECUTED.

**Owner role:** OpenStack distribution/service owners. Assign an actual owner before use.

**Baseline:** RA §18,22; VND §5; VC §4; K06–K08. [Main architecture](../../05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Worked design](../../05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Execution record](../MOP_Test_and_Handover_Template.docx).

## Required inputs

RB-00 and G1; exact distribution/services/backend, API policy, hardware, installer and provider tuple resolved.

Enter the actual site/service/tenant scope, design revision, exact supported component/API/provider/installer tuple, configuration artifact and protected credential reference. Every step must have an actual executor, completion signal, timeout/retry rule, observation, stop condition, data-safe recovery action and evidence location. No production address, credential, product count or universal native command is supplied.

## Controlled method

### RB-04-01 — Resolve selected services and backend

**Action:** Record Keystone, Nova/Placement, Neutron backend, Glance/Cinder and all offered data/trust/protection services.

**Expected observation:** No unsupported feature is inferred from generic OpenStack naming.

**Stop / preserve:** Distribution or backend uncertainty blocks affected design.

**Evidence:** Versioned service/extension matrix.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-04-02 — Install using supported lifecycle tooling

**Action:** Deploy the approved controllers/databases/messaging, compute and backend infrastructure under native ownership.

**Expected observation:** Control/data dependencies and quorum are observed.

**Stop / preserve:** Do not manage Neutron-owned OVN objects through a competing raw writer.

**Evidence:** Installer/native health and ownership receipts.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-04-03 — Enforce placement and data boundaries

**Action:** Configure actual scheduler/aggregate/trait eligibility, volume backend classes and image/key controls.

**Expected observation:** Tenant, zone and restart/restore constraints are effective.

**Stop / preserve:** Labels without enforced placement do not satisfy isolation.

**Evidence:** Scheduling decisions and data-attachment observations.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-04-04 — Protect network mutation authority

**Action:** Implement provider ownership of base mandatory groups, port security, address pairs, routers and external attachments through the supported role model.

**Expected observation:** Tenant permissions cannot attach an additive allow or disable required protection.

**Stop / preserve:** Unbounded tenant editing is not base-service qualification.

**Evidence:** API role tests and effective policy review.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-04-05 — Verify domain and service paths

**Action:** Build restricted distinct domains and handoffs; observe distributed routes, gateways, default egress normalization, metadata/boot services and replies.

**Expected observation:** Approved services work; connected/provider/floating-address shortcuts do not bypass controls.

**Stop / preserve:** Avoid blanket deny that hides broken initialization or IPv6 operation.

**Evidence:** Positive/negative path and native configuration evidence.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

### RB-04-06 — Qualify lifecycle and recovery

**Action:** Observe supported create/update/adopt/delete, task cleanup, gateway/host failure, Cinder isolation and restore.

**Expected observation:** Concrete tuple/service accepted or explicitly limited at G2.

**Stop / preserve:** Unknown residual ports/routes/grants remain defects.

**Evidence:** As-built, limitations, evidence and decision.

**Actual artifact / operator / UTC times / native task / outcome:** NOT RUN — complete in IT §2 and the implementation workbook.

## Completion and restart

The designated owner reviews actual observations and unresolved effects before the next package consumes the result. A failed or unknown operation stays owned and restricted until reconciled. Do not restore an old state file and describe it as rollback of infrastructure. Production activation requires the applicable initial operational/recovery readiness and valid operating authority; a restricted fixture cannot supply that authority.

These methods extend the baseline as proposed kit practice. They do not change the frozen source requirements or provide executable vendor adapters.
