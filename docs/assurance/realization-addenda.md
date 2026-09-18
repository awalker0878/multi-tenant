# RA realization addenda

Original fields are rendered below without rewriting their procedure, scope or not-run status. These are not newly executed results. [Family index](verification-families.md).

[Original records](../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/registers/realization_verification_addenda.json)

<a id="RA-01"></a>
## RA-01 — Independent native domain routing

**id:** RA-01

**title:** Independent native domain routing

**baseTests:** CT-003; CT-009; CT-023; CT-025

**chapters:** 8; 16; 17; 18

**procedure:** For the selected stack, enumerate native connected/distributed routes, defaults, provider/external attachments and upstream advertisements. Exercise the approved flow and its forbidden direct alternatives in both directions.

**expected:** Only the approved logical ZIP path is usable; native forwarding cannot bypass it.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-003](test-specifications.md#CT-003) · [CT-009](test-specifications.md#CT-009) · [CT-023](test-specifications.md#CT-023) · [CT-025](test-specifications.md#CT-025)

<a id="RA-02"></a>
## RA-02 — NSX isolated upstream reference

**id:** RA-02

**title:** NSX isolated upstream reference

**baseTests:** CT-003; CT-024; CT-080

**chapters:** 17

**procedure:** Verify the exact Tier-1, parent/VRF Tier-0, Edge and uplink topology. Review all route propagation and any inter-VRF leaking. Repeat through Edge failure and established-session changes.

**expected:** Independent domains remain isolated; the approved stateful path and session behaviour match the profile.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-003](test-specifications.md#CT-003) · [CT-024](test-specifications.md#CT-024) · [CT-080](test-specifications.md#CT-080)

<a id="RA-03"></a>
## RA-03 — Nutanix external attachment reference

**id:** RA-03

**title:** Nutanix external attachment reference

**baseTests:** CT-023; CT-024; CT-031

**chapters:** 16

**procedure:** Check external subnet connected paths, gateway reachability, NAT/no-NAT behaviour and return routing for each domain. Include neighbours and both offered address families.

**expected:** Sharing physical transport does not create direct VPC-to-VPC or workload-to-management access.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-023](test-specifications.md#CT-023) · [CT-024](test-specifications.md#CT-024) · [CT-031](test-specifications.md#CT-031)

<a id="RA-04"></a>
## RA-04 — OpenStack backend and authority reference

**id:** RA-04

**title:** OpenStack backend and authority reference

**baseTests:** CT-017; CT-021; CT-022; CT-066

**chapters:** 18

**procedure:** Verify chosen backend, Neutron policy, mandatory port/group controls, internal distributed routing and any floating/provider-network alternatives. Recheck after relocation.

**expected:** Tenant operations cannot remove mandatory isolation, create an unapproved external path or bypass the intended boundary.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-017](test-specifications.md#CT-017) · [CT-021](test-specifications.md#CT-021) · [CT-022](test-specifications.md#CT-022) · [CT-066](test-specifications.md#CT-066)

<a id="RA-05"></a>
## RA-05 — Physical and platform overlay demarcation

**id:** RA-05

**title:** Physical and platform overlay demarcation

**baseTests:** CT-032; CT-033; CT-034

**chapters:** 5

**procedure:** Verify platform tunnel reachability and effective MTU, fabric route/EVPN imports, multihoming failure and vendor handoff. Document all physical versus logical separation assumptions.

**expected:** Fabric interoperability does not import tenant routes or federate vendor overlays outside approved scope.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-032](test-specifications.md#CT-032) · [CT-033](test-specifications.md#CT-033) · [CT-034](test-specifications.md#CT-034)

<a id="RA-06"></a>
## RA-06 — Bootstrap ownership transition

**id:** RA-06

**title:** Bootstrap ownership transition

**baseTests:** CT-026; CT-027; CT-055

**chapters:** 21; 22

**procedure:** Recover initial access using only the declared independent bootstrap material. Transition to steady-state identity/tooling; revoke temporary credentials and recheck access.

**expected:** No circular recovery dependency or untracked residual bootstrap privilege remains.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-026](test-specifications.md#CT-026) · [CT-027](test-specifications.md#CT-027) · [CT-055](test-specifications.md#CT-055)

<a id="RA-07"></a>
## RA-07 — Composite provider authority

**id:** RA-07

**title:** Composite provider authority

**baseTests:** CT-019; CT-043; CT-044; CT-045

**chapters:** 20; 24

**procedure:** Provision one environment using the hosting, edge and name/address/protection scopes. Demonstrate each identity is denied changes outside its package and a downstream failure is recoverable.

**expected:** Coordination does not create a shared all-powerful state/identity or destroy shared/data resources on failure.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-019](test-specifications.md#CT-019) · [CT-043](test-specifications.md#CT-043) · [CT-044](test-specifications.md#CT-044) · [CT-045](test-specifications.md#CT-045)

<a id="RA-08"></a>
## RA-08 — Persistent platform versus temporary transfer networks

**id:** RA-08

**title:** Persistent platform versus temporary transfer networks

**baseTests:** CT-035; CT-054; CT-060; CT-076

**chapters:** 10; 27

**procedure:** Exercise supported live mobility/replication on provider transport and independently activate/expire a bounded cross-domain transfer connection.

**expected:** Persistent platform operation remains within its authority; temporary transfer access is removed without dismantling platform foundations.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-035](test-specifications.md#CT-035) · [CT-054](test-specifications.md#CT-054) · [CT-060](test-specifications.md#CT-060) · [CT-076](test-specifications.md#CT-076)

<a id="RA-09"></a>
## RA-09 — Brownfield non-destructive adoption

**id:** RA-09

**title:** Brownfield non-destructive adoption

**baseTests:** CT-044; CT-048; CT-070

**chapters:** 25

**procedure:** Inventory an authorized representative existing scope, confirm single configuration ownership, import/adopt and review the initial plan before mutation.

**expected:** No unapproved replacement or competing writer is introduced; adoption does not falsely assert compliance.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-044](test-specifications.md#CT-044) · [CT-048](test-specifications.md#CT-048) · [CT-070](test-specifications.md#CT-070)

<a id="RA-10"></a>
## RA-10 — Activation sequencing

**id:** RA-10

**title:** Activation sequencing

**baseTests:** CT-006; CT-007; CT-045; CT-069; CT-077

**chapters:** 23

**procedure:** Observe resource creation from reservation through denied network attachment, mandatory controls, internal checks and explicit exposure activation. Introduce a controlled failed activation check.

**expected:** No unprotected creation window; failed activation withdraws exposure while preserving data-safe recovery.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-006](test-specifications.md#CT-006) · [CT-007](test-specifications.md#CT-007) · [CT-045](test-specifications.md#CT-045) · [CT-069](test-specifications.md#CT-069) · [CT-077](test-specifications.md#CT-077)

<a id="RA-11"></a>
## RA-11 — Compute, management and storage sharing

**id:** RA-11

**title:** Compute, management and storage sharing

**baseTests:** CT-026; CT-035; CT-037; CT-078

**chapters:** 6; 7; 11; 12

**procedure:** Inspect actual host, management, storage/controller and transport sharing against adopted source tailoring. Test evacuation and copy operations without relying on labels alone.

**expected:** Actual co-residency and shared dependencies match the approved isolation design, including recovery states.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-026](test-specifications.md#CT-026) · [CT-035](test-specifications.md#CT-035) · [CT-037](test-specifications.md#CT-037) · [CT-078](test-specifications.md#CT-078)

<a id="RA-12"></a>
## RA-12 — Commissioned capacity and growth boundary

**id:** RA-12

**title:** Commissioned capacity and growth boundary

**baseTests:** CT-056; CT-071; CT-072; CT-074

**chapters:** 4; 22; 26

**procedure:** Provision within capacity, then exhaust a permitted attachment/resource pool in the test envelope. Follow the separate foundation growth path and reconcile inventory states.

**expected:** The workflow queues/rejects or selects eligible capacity; it does not rewire the fabric or weaken isolation as an undocumented tenant operation.

**executionStatus:** not-run

**safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

Related baseline procedures: [CT-056](test-specifications.md#CT-056) · [CT-071](test-specifications.md#CT-071) · [CT-072](test-specifications.md#CT-072) · [CT-074](test-specifications.md#CT-074)
