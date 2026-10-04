# Q06 — Policy equivalence

Q06 verifies R06–R08, R20 and R31. It supports P05 policy design, P07.04 native activation and relevant P09 expansions. G07.02 is the first native review; G08.04/G09.02 require reruns for changed migration or expansion topology. Equivalence means required allowed and denied outcomes survive native realization, including failure paths.

## Scope and ownership

Planning specifies portable flow intent and mandatory precedence. Platform/security owners identify actual enforcement and controlled interfaces; an independent security observer executes probes. E1/E2 can verify compilation and modeled behavior, but only E3 traffic observations on the exact topology establish native policy qualification.

Use the [domain model](../../product/domain-model.md), [requirements](../../implementation/requirements-and-qualification.md#2-domain-invariants) and [Permit Desk flows](../../product/application-walkthrough.md). OZ/RZ labels alone grant no permission. A ZIP is a controlled interface, with actual inspection and forward/reply path requirements.

## Preparation

1. Build a flow matrix identifying initiator, receiver, tenant/WSD/domain, protocol/port, address family, direction, connection state, expected allow/deny and required observation point.
2. Map each rule to enforcement objects, identity/selectors, mandatory precedence, route/NAT/inspection path and versioned native configuration.
3. Place probe workloads on the same host, same subnet, different hosts, separate domains and separate tenants. Include configured shared-service and edge paths.
4. Define allowed fault injection, failover topology, restoration steps and network impact limits with platform/security owners.
5. Confirm probe visibility through packet/session observations and independent endpoint checks; synchronize clocks and retain configuration snapshots.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q06.01 | Exercise authorized client→web, web→database and approved service flows | Required application transactions succeed over declared enforcement and reply paths | Flow matrix, application checks and packet/session observations |
| Q06.02 | Probe foreign-tenant→web/database, unapproved client→database and unsolicited reverse initiation | Denied sessions do not reach the protected application; attributable control observations match policy | Negative-flow results and observation-point records |
| Q06.03 | Repeat allowed/denied probes on same host, same subnet and different hosts | Local forwarding cannot bypass required isolation or inspection | Placement/config identities and per-path traffic results |
| Q06.04 | Attempt tag/label/identity selector tampering under tenant authority | Protected selector ownership prevents escalation; mandatory deny precedence remains effective | Authorization denial and post-attempt traffic results |
| Q06.05 | Exercise routed/edge/ZIP paths, NAT and asymmetric return conditions | Only declared initiations/replies work; unintended connected routes or inspection bypass fail | Route/NAT state, forward/reply traces and denied-path probes |
| Q06.06 | Test selected IPv4/IPv6 families and alternate reachable addresses | Required families preserve policy; unsupported required families block activation rather than bypass controls | Address-family matrix and activation hold |
| Q06.07 | Restart or fail the selected enforcement component within approved scope | Behavior meets the accepted fail-secure requirement; failover does not widen access | Fault timeline, surviving path and traffic observations |
| Q06.08 | Change policy under a fresh plan while probes continuously exercise allowed and denied paths | Rollout preserves mandatory constraints; rejected/partial policy keeps activation held | Versioned rules, continuous probes and rollback/recovery record |
| Q06.09 | Exercise shared DNS/time/identity/backup/logging paths and management access | Service access/replies are usable without unintended cross-tenant or workload-management transit | Service/management flow observations and denial matrix |
| Q06.10 | Move/recover workloads within the selected failure topology and repeat the matrix | Policy follows approved workload identity/placement; no widened access during recovery | Placement transitions, policy binding and repeated flow results |

## Execution and observations

Run probes long enough to cover the selected control-plane convergence and fault window; the approved operating target supplies duration and loss thresholds. Record successful connection/application behavior and absence at the protected endpoint. A firewall counter alone may not establish the actual packet path.

Separate denial caused by absent routing from denial enforced by the required control. If a routing repair would open an unprotected path, the realization does not meet the declared security requirement.

When a topology feature is outside selected scope, record the exact exclusion and ensure assessment/admission rejects workloads requiring it. Do not describe a missing IPv6 test as proof that IPv6 is disabled everywhere.

## Pass criteria and evidence

Every mandatory positive and negative row must pass across the selected placements and failure conditions. No same-host/subnet, selector, route, shared-service or return-path bypass is acceptable. Service availability and fail-secure behavior must both meet the accepted scope.

Retain portable policy/profile versions, actual enforcement configuration identities, topology/placement maps, flow results, packet/session evidence, rule ownership tests and fault timelines. Bind E3 evidence to exact tuple and G07/G08/G09 criteria in the [delivery register](../../implementation/delivery-register.yaml).

## Cleanup and reruns

Restore approved routing/enforcement configuration and verify the denied-flow matrix after cleanup. Remove only test-owned probes/rules. Rerun affected paths after platform, enforcement, topology, selector, service insertion, NAT, address-family or guest-network changes.
