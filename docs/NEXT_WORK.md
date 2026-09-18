# Remaining implementation from the current repository state

This page is the forward-looking work list. It no longer treats the preserved Increment02–04 backlog as if it were the current implementation state.

Read [current I01–I10 status](implementation/current-status.md) for the maintained repository/local evidence view. The original [implementation backlog](../sources/implementation_backlog.csv) remains preserved for historical traceability.

## Repository and local work now implemented

The current repository includes bounded evidence for:

- Terraform 1.13.5 engine validation of the ten module/root pairs, real provider schemas, committed lock review and plan-only provider mocks;
- separate routed IPv4 and IPv6 Linux packet/TLS fixtures, including origin-specific service replies, containment, failure/recovery and PMTU observations;
- selected NSX, Nutanix and Neutron readback candidates, including bounded Nutanix task-tree observation and offline interrupted-change review;
- local DNS and TLS/service-identity integration fixtures;
- a source-backed native commissioning kit with 22 engineering inputs, 11 work packages and 12 W14 observation groups;
- a machine-readable three-platform capability registry that currently has zero native-qualified capabilities;
- a fail-closed platform-family pre-placement check whose current expected result is `HOLD_NO_NATIVE_QUALIFIED_PLATFORM`.

These are repository implementation, engine checks, local protocol/packet evidence or planning records. They are **not** native site qualification or production authorization.

## Required next work

| Priority / ownership | Required next work | Hold point |
|---|---|---|
| Platform and security owner | Select the installed site/cell, platform/API/provider/licence tuple and actual EC/SE firewall/context/attachment implementation. Record the permitted disposable qualification scope. | Before native connection or provisioning |
| Placement/capacity owner | Establish site/cell/service-class eligibility, zone/co-residency decision, quota, surviving compute/storage capacity, addresses and security-edge capacity. | Before reservation or workload allocation |
| Platform qualification owners | Qualify the selected Nutanix, VMware/NSX or OpenStack tuple against the actual APIs, defaults, policy hierarchy, scheduler/placement behavior, native IPv4/IPv6 and failure topology. Promote only demonstrated capabilities to `NATIVE_QUALIFIED`. | Before platform-family eligibility can pass |
| Platform observers | Exercise the exact readback profiles against real APIs/RBAC/version tokens; add VM/Flow/route/large-task coverage only where the selected native operations require it. | Before relying on native readback |
| Recovery owner | Implement and demonstrate true scoped writer fencing, state reconciliation, controlled forward repair/import and data-safe retirement. Record-only recovery review does not supply these actions. | Before resuming interrupted mutations |
| Security/network owner | Build and observe actual domain/service attachments, routing, mandatory policy/inspection, management exclusion, HA and complete ZIP/security-boundary paths. | Before approved connectivity |
| Shared-service owners | Integrate authoritative IPAM/DNS, identity/PKI/KMS, time/images/logging, storage/protection and backup; prove origin-specific replies and isolated useful-data restore. | Before offered service promises |
| IPv6 engineering | Qualify IPv6 on the selected native stacks, security edges and shared-service paths, including supported local protocols, overlay MTU and HA. Local namespace results remain supporting evidence only. | Before native IPv6/dual-stack offer |
| Operations and authority | Complete G0/G1/G2 and applicable initial G4 evidence, service ownership/objectives, reversible G3 activation and post-activation checks. | Before production activation |

## Stop conditions

Do not work around these gaps by:

- changing a mandatory capability to optional;
- treating candidate Terraform source, documentation or local fixtures as native qualification;
- allowing a vendor scheduler to choose outside an already accepted site/cell/pool;
- replacing a missing dedicated/zone-specific pool with shared placement;
- replaying an uncertain native change instead of discovering current state;
- releasing incident containment through ordinary reconciliation;
- declaring Service Ready from code merge or CI alone.

[Current implementation status](implementation/current-status.md) · [Implementation map](implementation/code-map.md) · [Native commissioning](implementation/native-reference/README.md)
