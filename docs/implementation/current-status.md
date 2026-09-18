# Current implementation status

**Purpose:** provide a maintained view of repository implementation progress without rewriting the preserved Increment02–04 backlog or turning local/CI evidence into native qualification.

Reviewed baseline: <code>fb2316e8aee3469e7e52ee4887fa6b972806f44b</code>.

Historical source: [preserved implementation backlog](../../sources/implementation_backlog.csv) · Git blob <code>b7cc1dd095a96ca1832a698d49d9ee4182806e01</code>.

Every item below remains **NOT_RUN** for actual native target contact and native qualification, and **NOT_ISSUED** for formal authorization. A repository implementation, engine test, or local fixture is therefore not a production-ready service claim.

## Summary

| ID | Original work item | Current repository state | Evidence level | Native / authorization |
| --- | --- | --- | --- | --- |
| I01 | Terraform engine, schemas and mocked plans | <code>ENGINE_VALIDATED_NATIVE_TARGET_OPEN</code> | <code>ENGINE_CI</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I02 | Selected actual target tuple | <code>SITE_SELECTION_OPEN</code> | <code>OPEN_DECISION</code>, <code>PLANNING_ONLY</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I03 | Effective quarantine | <code>LOCAL_QUARANTINE_FIXTURE_NATIVE_OPEN</code> | <code>CANDIDATE_SOURCE</code>, <code>LOCAL_PACKET_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I04 | EC/SE native security edge | <code>EDGE_CANDIDATE_NATIVE_OPEN</code> | <code>CANDIDATE_SOURCE</code>, <code>LOCAL_PACKET_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I05 | Origin-specific service reply routes | <code>LOCAL_REPLY_ROUTE_FIXTURE_NATIVE_SERVICE_OPEN</code> | <code>CANDIDATE_SOURCE</code>, <code>LOCAL_PACKET_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I06 | IPAM, DNS and bootstrap | <code>LOCAL_DNS_INTEGRATION_NATIVE_IPAM_OPEN</code> | <code>CANDIDATE_SOURCE</code>, <code>LOCAL_PROTOCOL_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I07 | Identity, keys, storage and protection | <code>LOCAL_IDENTITY_FIXTURE_NATIVE_TRUST_PROTECTION_OPEN</code> | <code>LOCAL_PROTOCOL_FIXTURE</code>, <code>LOCAL_PACKET_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I08 | IPv6 native and packet extension | <code>ROUTED_DUAL_STACK_FIXTURE_NATIVE_STACK_OPEN</code> | <code>LOCAL_PACKET_FIXTURE</code>, <code>LOCAL_PROTOCOL_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I09 | Read-back, drift and uncertain operations | <code>READBACK_CANDIDATES_LOCAL_FIXTURE_NATIVE_OPEN</code> | <code>CANDIDATE_SOURCE</code>, <code>LOCAL_HTTPS_FIXTURE</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |
| I10 | Activation and initial operating readiness | <code>READINESS_PLANNING_ACTIVATION_OPEN</code> | <code>PLANNING_ONLY</code>, <code>ENGINEERING_PRECHECK</code> | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |

## Interpretation

The historical CSV records what earlier increments reported. This page is the current overlay. It may advance when repository implementation or bounded local evidence advances, but it must not relabel historical results or close native/site hold points without the required external evidence.

## I01 — Terraform engine, schemas and mocked plans

Current state: <code>ENGINE_VALIDATED_NATIVE_TARGET_OPEN</code>.

Evidence levels: <code>ENGINE_CI</code>.

Repository evidence:
- [tools/verify_terraform.py](../../tools/verify_terraform.py)
- [scripts/check_dependency_locks.py](../../scripts/check_dependency_locks.py)
- [.github/workflows/validate.yml](../../.github/workflows/validate.yml)

Remaining evidence:
- selected installed target tuple and permitted scope
- live provider/API compatibility and native defaults
- approved native plan/apply procedure and target evidence

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I02 — Selected actual target tuple

Current state: <code>SITE_SELECTION_OPEN</code>.

Evidence levels: <code>OPEN_DECISION</code> · <code>PLANNING_ONLY</code>.

Repository evidence:
- [docs/implementation/native-reference/site-inputs.md](native-reference/site-inputs.md)
- [sources/commissioning/native_reference_plan.json](../../sources/commissioning/native_reference_plan.json)

Remaining evidence:
- installed hardware/product/API/provider/licence tuple
- security-edge implementation and permitted disposable target scope
- owner-reviewed site/cell/service-class decision

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I03 — Effective quarantine

Current state: <code>LOCAL_QUARANTINE_FIXTURE_NATIVE_OPEN</code>.

Evidence levels: <code>CANDIDATE_SOURCE</code> · <code>LOCAL_PACKET_FIXTURE</code>.

Repository evidence:
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [lab/run_ipv6_lab.py](../../lab/run_ipv6_lab.py)

Remaining evidence:
- native same-host and distributed enforcement
- policy precedence and protected identity selectors
- native failure and recovery observations on the selected stack

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I04 — EC/SE native security edge

Current state: <code>EDGE_CANDIDATE_NATIVE_OPEN</code>.

Evidence levels: <code>CANDIDATE_SOURCE</code> · <code>LOCAL_PACKET_FIXTURE</code>.

Repository evidence:
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [lab/run_ipv6_lab.py](../../lab/run_ipv6_lab.py)

Remaining evidence:
- selected production security-edge/context implementation
- actual interfaces, identity controls, inspection and management separation
- HA and complete ZIP/security-boundary equivalence

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I05 — Origin-specific service reply routes

Current state: <code>LOCAL_REPLY_ROUTE_FIXTURE_NATIVE_SERVICE_OPEN</code>.

Evidence levels: <code>CANDIDATE_SOURCE</code> · <code>LOCAL_PACKET_FIXTURE</code>.

Repository evidence:
- [tools/route_audit.py](../../tools/route_audit.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [lab/run_ipv6_lab.py](../../lab/run_ipv6_lab.py)

Remaining evidence:
- implementation in the actual service/gateway owner tools
- origin-specific native return paths
- native telemetry and failure/recovery evidence

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I06 — IPAM, DNS and bootstrap

Current state: <code>LOCAL_DNS_INTEGRATION_NATIVE_IPAM_OPEN</code>.

Evidence levels: <code>CANDIDATE_SOURCE</code> · <code>LOCAL_PROTOCOL_FIXTURE</code>.

Repository evidence:
- [tools/dns_change.py](../../tools/dns_change.py)
- [lab/run_dns_lab.py](../../lab/run_dns_lab.py)
- [docs/DNS_LIFECYCLE.md](../DNS_LIFECYCLE.md)

Remaining evidence:
- authoritative IPAM allocation and reuse controls
- actual DNS update ACLs, propagation and resolver behavior
- DHCP/metadata/bootstrap and name/time/image service integration

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I07 — Identity, keys, storage and protection

Current state: <code>LOCAL_IDENTITY_FIXTURE_NATIVE_TRUST_PROTECTION_OPEN</code>.

Evidence levels: <code>LOCAL_PROTOCOL_FIXTURE</code> · <code>LOCAL_PACKET_FIXTURE</code>.

Repository evidence:
- [lab/mtls_fixture.py](../../lab/mtls_fixture.py)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [lab/run_ipv6_lab.py](../../lab/run_ipv6_lab.py)

Remaining evidence:
- actual identity/PKI/KMS clients and trust lifecycle
- storage/protection integration
- isolated useful-data restore with independent key/catalogue dependencies

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I08 — IPv6 native and packet extension

Current state: <code>ROUTED_DUAL_STACK_FIXTURE_NATIVE_STACK_OPEN</code>.

Evidence levels: <code>LOCAL_PACKET_FIXTURE</code> · <code>LOCAL_PROTOCOL_FIXTURE</code>.

Repository evidence:
- [lab/run_ipv6_lab.py](../../lab/run_ipv6_lab.py)
- [docs/engineering/routed-ipv6-qualification.md](../engineering/routed-ipv6-qualification.md)
- [sources/implementation/routed_ipv6.json](../../sources/implementation/routed_ipv6.json)

Remaining evidence:
- native IPv6 routing, local protocols and enforcement for each offered stack
- native edge/shared-service path and overlay MTU behavior
- vendor HA and complete offered-family qualification

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I09 — Read-back, drift and uncertain operations

Current state: <code>READBACK_CANDIDATES_LOCAL_FIXTURE_NATIVE_OPEN</code>.

Evidence levels: <code>CANDIDATE_SOURCE</code> · <code>LOCAL_HTTPS_FIXTURE</code>.

Repository evidence:
- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)
- [tools/recovery_review.py](../../tools/recovery_review.py)
- [sources/implementation/nutanix_task_tree.json](../../sources/implementation/nutanix_task_tree.json)

Remaining evidence:
- actual API/RBAC/default and version-token qualification
- complete inventory/VM/Flow/route/composite-task coverage where required
- true scoped writer fencing and authorized repair/import/retirement

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## I10 — Activation and initial operating readiness

Current state: <code>READINESS_PLANNING_ACTIVATION_OPEN</code>.

Evidence levels: <code>PLANNING_ONLY</code> · <code>ENGINEERING_PRECHECK</code>.

Repository evidence:
- [scripts/commissioning_pack.py](../../scripts/commissioning_pack.py)
- [sources/commissioning/native_reference_plan.json](../../sources/commissioning/native_reference_plan.json)
- [scripts/check_platform_family_eligibility.py](../../scripts/check_platform_family_eligibility.py)
- [sources/implementation/platform_family_eligibility.json](../../sources/implementation/platform_family_eligibility.json)

Remaining evidence:
- accepted G0/G1/G2 and applicable initial G4 evidence
- selected site/cell/pool and reversible G3 activation procedure
- post-activation checks, ownership, service objectives and formal authorization

Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.

## Maintenance rule

Update <code>sources/implementation/current_status.json</code> first. The checker validates I01–I10, repository evidence paths, the preserved historical backlog blob, explicit OPEN/HOLD state and the non-authorization boundary. Regenerate or update this page to match that source; do not edit the historical increment rows to make current progress look older.

[Next work](../NEXT_WORK.md) · [Implementation map](code-map.md) · [Native reference commissioning](native-reference/README.md)
