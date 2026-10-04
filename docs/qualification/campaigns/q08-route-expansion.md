# Q08 — Route expansion

Q08 verifies R26–R28 and selected expansion obligations in R07–R13/R19–R21. It supports P09.01–P09.05 and G09.01–G09.04. Every advertised direction, method, guest and topology requires its own bounded qualification record. A tranche may select a subset, but deferred routes remain outside the release claim.

## Scope and ownership

Product and architecture freeze the tranche; platform/guest/data owners implement the selected scope; security and qualification independently review native outcomes. E1/E2 adapter conformance precedes E3 native qualification. Q08 composes the relevant Q02/Q04–Q07 procedures rather than weakening their obligations for another platform.

The six directed cross-platform routes are VMware→AHV, VMware→OpenStack, AHV→VMware, AHV→OpenStack, OpenStack→VMware and OpenStack→AHV. The first route already tested in Q07 can contribute only evidence whose exact release/tuple scope remains valid after impact review. Same-family relocation is an additional topology-specific operation.

## Preparation

1. Freeze the selected route rows with operation/method, exact installed tuples, guest/image, data profile, policy/service topology, failure model and artifacts.
2. Define exclusions for appliance/no-guest-mutation, Windows, firmware, shared disks, encryption/vTPM, devices, warm/live movement and database synchronization.
3. Assign qualified observers, separately scoped laboratory authorizations, resource budgets, recovery authority and owned cleanup scope per row.
4. Select the Q02/Q04/Q05/Q06/Q07 cases each row inherits, identify added cases and justify any reviewed non-applicability.
5. Prepare concurrent wave fixtures with dependency DAGs, tenant priorities/windows and shared endpoint/impact budgets from approved operating targets.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q08.01 | Run each selected adapter through contracts, identity/scope denial and unknown-outcome conformance | Platform extension preserves context authority, operation journal and uncertainty semantics | Adapter version and conformance report |
| Q08.02 | Execute positive, negative and recovery cases for each directed route row | Each row meets its own Q07-equivalent method/data/recovery requirements; reverse success is never inferred | Route-specific E3 dossier and case mapping |
| Q08.03 | Exercise selected Linux/Windows/appliance profiles, including prohibited guest mutation | Declared boot/drivers/identity and hardening boundaries hold; unsupported features block before writes | Guest/image cases, denial and native observations |
| Q08.04 | Exercise selected whole-VM conversion or database synchronization variants | Method-specific disk/device/consistency/fencing and post-write recovery pass independently | Method/dataset manifests and recovery evidence |
| Q08.05 | Exercise each selected same-family relocation/failure-domain topology | Placement, storage/network dependencies and recovery meet that topology's scope | Topology-specific resource and recovery observations |
| Q08.06 | Perform selected brownfield no-change import, conflict/drift and detach cases | Q02 ownership-transfer rules hold; old writers cannot mutate imported scope | Q02.08–Q02.10 evidence and ownership map |
| Q08.07 | Apply day-two resize, policy, patching, service or certificate change under exact plans | Only owned fields change; required availability/policy and recoverability persist | Change plan, native diff and Q04/Q06 reruns |
| Q08.08 | Schedule competing waves with shared dependencies, endpoint limits and change windows | Dependency order, tenant fairness and bounded concurrent impact meet approved budgets | Scheduler timeline and measured owner/endpoint load |
| Q08.09 | Pause/stop a wave while effects are queued, active and uncertain | No prohibited new effects start; accepted effects reconcile; downstream work remains held as required | Wave-state and native journal/fencing observations |
| Q08.10 | Upgrade or replace an adapter and present incompatible contracts/qualification | Compatible version routing works; incompatible or unqualified scope is rejected; affected support is reevaluated | Version-transition report and admission denials |

## Execution and observations

Allocate a distinct run ID for every tuple/method row. Keep campaign evidence shared only where the behavior, artifacts and environment are demonstrably identical and the reviewer records the reuse rationale.

Use the separately scoped laboratory lane to qualify a new tuple; do not require that same tuple to have prior operational qualification. Ordinary operational admission remains blocked until reviewed exact-tuple evidence is published and the release scope is accepted.

Treat newly exposed feature combinations as new scope. For example, passing Linux cold migration on one network backend does not establish Windows, warm transfer, appliance, IPv6 or a different security realization.

## Pass criteria and evidence

Every row advertised for the selected tranche must satisfy its mandatory contract, native, security and recovery cases. Tranche completion requires explicit deferred rows and revised scope where any selected feature cannot pass; a partial route matrix cannot represent the complete R26 obligation.

Store the tranche baseline, per-row run manifests, conformance reports, Q02/Q04–Q07 mappings, native evidence, scheduling measurements, limitations and independent review. Update the [support matrix](../../implementation/support-matrix.md) only from actual accepted scope and the [delivery register](../../implementation/delivery-register.yaml).

## Cleanup and reruns

Reconcile active/unknown operations before retiring owned test resources and releasing budgets. Preserve source/target recovery datasets required by each route. Rerun changed rows and affected common cases when adapters, platform features, guest/method, enforcement, scheduling or recovery changes.
