# Q11 qualification observation cards

Original fields are rendered below without rewriting their procedure, scope or not-run status. These are not newly executed results. [Family index](verification-families.md).

[Original records](../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/development/qualification_observation_cards.csv)

<a id="Q11-01"></a>
## Q11-01 — approved path and reply

**id:** Q11-01

**title:** approved path and reply

**existing_test_ids:** CT-003; CT-007; CT-024

**procedure_and_control:** Verify both endpoints; exercise F14-01. Locate the effective forward and reply path at native gateways and EC-01. Try a separately scoped reverse initiation.

**expected_result_and_artifacts:** Declared TCP/443 operation and reply work; unapproved new reverse initiation is denied. Retain path/rule/session evidence, not only an application success.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_03

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-003](test-specifications.md#CT-003) · [CT-007](test-specifications.md#CT-007) · [CT-024](test-specifications.md#CT-024)

<a id="Q11-02"></a>
## Q11-02 — tenant isolation

**id:** Q11-02

**title:** tenant isolation

**existing_test_ids:** CT-001; CT-002

**procedure_and_control:** Prove each tenant’s local approved service. Observe bounded disallowed cross-tenant attempts in both directions and each offered family.

**expected_result_and_artifacts:** No unauthorized communication. Record endpoints, intended control, actual routing/policy and attributable denials. Unhealthy controls block the result.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_03

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-001](test-specifications.md#CT-001) · [CT-002](test-specifications.md#CT-002)

<a id="Q11-03"></a>
## Q11-03 — same-domain policy

**id:** Q11-03

**title:** same-domain policy

**existing_test_ids:** CT-021; CT-022

**procedure_and_control:** Place the temporary probe in one approved domain; verify same-host/cross-host cases where applicable. Compare approved and unapproved communication.

**expected_result_and_artifacts:** Mandatory policy applies without requiring a physical gateway hop. Retain placement and enforcement evidence and the probe cleanup receipt.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_03

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-021](test-specifications.md#CT-021) · [CT-022](test-specifications.md#CT-022)

<a id="Q11-04"></a>
## Q11-04 — shared-service return

**id:** Q11-04

**title:** shared-service return

**existing_test_ids:** CT-008; CT-023; CT-024

**procedure_and_control:** Exercise the same resolver from both tenants. Trace each reply through its own SE/EC chain; check unbound service/admin targets and alternative connected paths.

**expected_result_and_artifacts:** Only entitled service use and origin-specific replies succeed. Retain service-side and edge observations; a shared endpoint is not tenant transit.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_03

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-008](test-specifications.md#CT-008) · [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024)

<a id="Q11-05"></a>
## Q11-05 — mandatory mutation authority

**id:** Q11-05

**title:** mandatory mutation authority

**existing_test_ids:** CT-019; CT-020; CT-022; CT-066

**procedure_and_control:** With the actual tenant role, request forbidden baseline/group/port/external changes. Separately perform one approved workload operation.

**expected_result_and_artifacts:** Forbidden native mutations fail; entitled operation works. Record principal, target, operation and effective permission without storing secrets.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_04

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-019](test-specifications.md#CT-019) · [CT-020](test-specifications.md#CT-020) · [CT-022](test-specifications.md#CT-022) · [CT-066](test-specifications.md#CT-066)

<a id="Q11-06"></a>
## Q11-06 — data attachment and copy scope

**id:** Q11-06

**title:** data attachment and copy scope

**existing_test_ids:** CT-037; CT-078

**procedure_and_control:** Create disposable owned data and a known integrity marker. Test authorized access and bounded foreign attachment/clone/export attempts.

**expected_result_and_artifacts:** Owned access works; unauthorized data or lower-scope copy access fails. Retain data-service decisions, copy lineage and cleanup.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_04

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-037](test-specifications.md#CT-037) · [CT-078](test-specifications.md#CT-078)

<a id="Q11-07"></a>
## Q11-07 — identity and key lifecycle

**id:** Q11-07

**title:** identity and key lifecycle

**existing_test_ids:** CT-028; CT-038; CT-079

**procedure_and_control:** Use disposable credentials/key material in an approved scope. Observe valid use, rotation/revocation and denied foreign or revoked use.

**expected_result_and_artifacts:** Required use remains attributable; old authority expires as designed. Retain issuer/service logs and timestamps; no plaintext fallback.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_04

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-028](test-specifications.md#CT-028) · [CT-038](test-specifications.md#CT-038) · [CT-079](test-specifications.md#CT-079)

<a id="Q11-08"></a>
## Q11-08 — service protocols and MTU

**id:** Q11-08

**title:** service protocols and MTU

**existing_test_ids:** CT-008; CT-030; CT-031; CT-032

**procedure_and_control:** Exercise DNS UDP/TCP and controlled fallback; check authorized resolver only. Test actual workload packet budget, PMTU and offered families end to end.

**expected_result_and_artifacts:** Necessary protocol behaviour works without broad egress or alternate-path bypass. Retain family/path matrix, packet budget and observed outcomes.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_04

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-008](test-specifications.md#CT-008) · [CT-030](test-specifications.md#CT-030) · [CT-031](test-specifications.md#CT-031) · [CT-032](test-specifications.md#CT-032)

<a id="Q11-09"></a>
## Q11-09 — edge or link loss

**id:** Q11-09

**title:** edge or link loss

**existing_test_ids:** CT-012; CT-024; CT-034

**procedure_and_control:** Under approved representative load, observe the selected node/link failure and restoration using the site MOP. Capture new and established sessions.

**expected_result_and_artifacts:** Security: no bypass. Service: actual interruption and surviving load. Recovery: correct route/state after restoration.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_05

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-012](test-specifications.md#CT-012) · [CT-024](test-specifications.md#CT-024) · [CT-034](test-specifications.md#CT-034)

<a id="Q11-10"></a>
## Q11-10 — dependency loss

**id:** Q11-10

**title:** dependency loss

**existing_test_ids:** CT-011; CT-027; CT-038; CT-050; CT-055

**procedure_and_control:** Observe one scoped management, identity, key, logging or state dependency loss at a time; follow its accepted recovery procedure.

**expected_result_and_artifacts:** No fallback privilege/permit/plaintext. Existing and new operations match the documented limits. Evidence gaps and recovery time remain visible.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_05

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-011](test-specifications.md#CT-011) · [CT-027](test-specifications.md#CT-027) · [CT-038](test-specifications.md#CT-038) · [CT-050](test-specifications.md#CT-050) · [CT-055](test-specifications.md#CT-055)

<a id="Q11-11"></a>
## Q11-11 — uncertain provisioning outcome

**id:** Q11-11

**title:** uncertain provisioning outcome

**existing_test_ids:** CT-045; CT-046; CT-048

**procedure_and_control:** In a disposable scope, interrupt a response or executor at an approved point. Freeze competing writes; discover actual native tasks and resources before recovery.

**expected_result_and_artifacts:** No duplicate allocation or unsafe deletion. Denied unfinished resources remain owned. Retain task, plan, state and actual-outcome reconciliation.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_05

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-045](test-specifications.md#CT-045) · [CT-046](test-specifications.md#CT-046) · [CT-048](test-specifications.md#CT-048)

<a id="Q11-12"></a>
## Q11-12 — isolated restore and cutover

**id:** Q11-12

**title:** isolated restore and cutover

**existing_test_ids:** CT-052; CT-053; CT-054; CT-060

**procedure_and_control:** Restore a known disposable dataset and dependencies into the authorized recovery domain; validate consistency, identity/keys and paths before controlled activation.

**expected_result_and_artifacts:** Useful data and measured RTO/RPO; no ambiguous simultaneous writer; protection, return path and operating ownership survive cutover.

**document_path:** 03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx

**bookmark:** QCP_05

**execution_status:** not-run

**actual_target:** [Unfilled original response field]

**observed_result:** [Unfilled original response field]

**evidence_reference:** [Unfilled original response field]

**reviewer:** [Unfilled original response field]

**scope_note:** Elaboration of inherited procedures, not a new control or executed result.

Related baseline procedures: [CT-052](test-specifications.md#CT-052) · [CT-053](test-specifications.md#CT-053) · [CT-054](test-specifications.md#CT-054) · [CT-060](test-specifications.md#CT-060)
