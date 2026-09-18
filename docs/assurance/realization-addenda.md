# Native realization addenda — RA-01 to RA-12

These are the retained supplemental procedures, not a new set of executed tests. Each elaborates the CT references shown and retains its original not-run state. Select by actual stack, offered service and accepted test safety envelope.

[Unchanged source JSON](../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/registers/realization_verification_addenda.json)

<a id="RA-01"></a>
## RA-01 — Independent native domain routing

**State:** not-run. **Base procedures:** CT-003, CT-009, CT-023, CT-025.

For the selected stack, enumerate native connected/distributed routes, defaults, provider/external attachments and upstream advertisements. Exercise the approved flow and its forbidden direct alternatives in both directions.

**Expected:** Only the approved logical ZIP path is usable; native forwarding cannot bypass it.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md) · [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md)

<a id="RA-02"></a>
## RA-02 — NSX isolated upstream reference

**State:** not-run. **Base procedures:** CT-003, CT-024, CT-080.

Verify the exact Tier-1, parent/VRF Tier-0, Edge and uplink topology. Review all route propagation and any inter-VRF leaking. Repeat through Edge failure and established-session changes.

**Expected:** Independent domains remain isolated; the approved stateful path and session behaviour match the profile.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §17](../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md)

<a id="RA-03"></a>
## RA-03 — Nutanix external attachment reference

**State:** not-run. **Base procedures:** CT-023, CT-024, CT-031.

Check external subnet connected paths, gateway reachability, NAT/no-NAT behaviour and return routing for each domain. Include neighbours and both offered address families.

**Expected:** Sharing physical transport does not create direct VPC-to-VPC or workload-to-management access.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md)

<a id="RA-04"></a>
## RA-04 — OpenStack backend and authority reference

**State:** not-run. **Base procedures:** CT-017, CT-021, CT-022, CT-066.

Verify chosen backend, Neutron policy, mandatory port/group controls, internal distributed routing and any floating/provider-network alternatives. Recheck after relocation.

**Expected:** Tenant operations cannot remove mandatory isolation, create an unapproved external path or bypass the intended boundary.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md)

<a id="RA-05"></a>
## RA-05 — Physical and platform overlay demarcation

**State:** not-run. **Base procedures:** CT-032, CT-033, CT-034.

Verify platform tunnel reachability and effective MTU, fabric route/EVPN imports, multihoming failure and vendor handoff. Document all physical versus logical separation assumptions.

**Expected:** Fabric interoperability does not import tenant routes or federate vendor overlays outside approved scope.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md)

<a id="RA-06"></a>
## RA-06 — Bootstrap ownership transition

**State:** not-run. **Base procedures:** CT-026, CT-027, CT-055.

Recover initial access using only the declared independent bootstrap material. Transition to steady-state identity/tooling; revoke temporary credentials and recheck access.

**Expected:** No circular recovery dependency or untracked residual bootstrap privilege remains.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §21](../architecture/reference/21-day-0-bootstrap-and-physical-commissioning.md) · [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md)

<a id="RA-07"></a>
## RA-07 — Composite provider authority

**State:** not-run. **Base procedures:** CT-019, CT-043, CT-044, CT-045.

Provision one environment using the hosting, edge and name/address/protection scopes. Demonstrate each identity is denied changes outside its package and a downstream failure is recoverable.

**Expected:** Coordination does not create a shared all-powerful state/identity or destroy shared/data resources on failure.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §20](../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md) · [RA §24](../architecture/reference/24-terraform-across-the-vendor-stacks.md)

<a id="RA-08"></a>
## RA-08 — Persistent platform versus temporary transfer networks

**State:** not-run. **Base procedures:** CT-035, CT-054, CT-060, CT-076.

Exercise supported live mobility/replication on provider transport and independently activate/expire a bounded cross-domain transfer connection.

**Expected:** Persistent platform operation remains within its authority; temporary transfer access is removed without dismantling platform foundations.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md)

<a id="RA-09"></a>
## RA-09 — Brownfield non-destructive adoption

**State:** not-run. **Base procedures:** CT-044, CT-048, CT-070.

Inventory an authorized representative existing scope, confirm single configuration ownership, import/adopt and review the initial plan before mutation.

**Expected:** No unapproved replacement or competing writer is introduced; adoption does not falsely assert compliance.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §25](../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md)

<a id="RA-10"></a>
## RA-10 — Activation sequencing

**State:** not-run. **Base procedures:** CT-006, CT-007, CT-045, CT-069, CT-077.

Observe resource creation from reservation through denied network attachment, mandatory controls, internal checks and explicit exposure activation. Introduce a controlled failed activation check.

**Expected:** No unprotected creation window; failed activation withdraws exposure while preserving data-safe recovery.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §23](../architecture/reference/23-tenant-domain-and-workload-provisioning-sequence.md)

<a id="RA-11"></a>
## RA-11 — Compute, management and storage sharing

**State:** not-run. **Base procedures:** CT-026, CT-035, CT-037, CT-078.

Inspect actual host, management, storage/controller and transport sharing against adopted source tailoring. Test evacuation and copy operations without relying on labels alone.

**Expected:** Actual co-residency and shared dependencies match the approved isolation design, including recovery states.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [RA §12](../architecture/reference/12-storage-backup-and-data-isolation-architecture.md)

<a id="RA-12"></a>
## RA-12 — Commissioned capacity and growth boundary

**State:** not-run. **Base procedures:** CT-056, CT-071, CT-072, CT-074.

Provision within capacity, then exhaust a permitted attachment/resource pool in the test envelope. Follow the separate foundation growth path and reconcile inventory states.

**Expected:** The workflow queues/rejects or selects eligible capacity; it does not rewire the fabric or weaken isolation as an undocumented tenant operation.

**Safety:** Execute only within an authorized representative test environment or explicitly approved production safety envelope.

**Parent architecture:** [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §22](../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md)
