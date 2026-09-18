# 43. State boundaries, cross-state transactions and partial failure

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13379_1645000677"></a>
<a id="sec_43"></a>

State boundaries are blast-radius and authority boundaries. Use separate state for physical foundation, management, shared security edge, domain realization, workloads and shared service ownership, with the smallest practical lifecycle scope inside each. One actor may not own all domains of authority simply because Terraform can reach them. State and plan artifacts can contain sensitive infrastructure and credential material and require appropriate protection.


<a id="source-table-598"></a>

| State/actor | Owns | Cross-state exchange |
| --- | --- | --- |
| Foundation | Underlay and physical attachment capacity | Versioned attachment/capability outputs, not shared credentials |
| Management | MZ/OOB and privileged access services | Approved administrative endpoints and trust metadata |
| Security edge | ZIP contexts, baseline and exposure policy | Approved adjacency, policy and readiness references |
| Domain | Routing/network realization and mandatory workload policy | Instance/network IDs and provider-internal allocation receipt |
| Workload | VMs/data attachments and entitled application objects | Stable WSD identity and approved network/service references |
| Shared service | Provider endpoint and service data/control ownership | Versioned binding contract and health/evidence references |

Terraform does not provide an atomic transaction across these states and external IPAM/DNS/inventory services. The controller implements an explicit staged/saga-style operation: reserve, create denied infrastructure, configure boundary, validate, activate, and commit evidence. Each stage records a completion token and an authorized compensation action. Compensations must preserve held data and shared resources; “rollback” is not an excuse to destroy a resource that may contain new data.

Avoid granting remote-state read access just to retrieve a convenient output because it can expose more sensitive state than intended. Publish minimal versioned output contracts through an access-controlled registry when suitable. State backend locking/versioning, protected backups, audit and disaster recovery are tested. Restoring a prior state file does not restore infrastructure; reconcile real resources and generations before any further apply. Emergency lock removal requires proof the writer has stopped and an accountable recovery procedure.

<a id="req_STATE_001"></a>

STATE-001  No single routine tenant automation identity SHALL have authority to modify physical fabric, management foundation, security edge, and tenant workloads simultaneously.

Automation platform  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_STATE_002"></a>

STATE-002  Remote state backends SHALL use encryption, strong authentication, locking, recovery/versioning, access logging, and separation appropriate to the sensitivity of contained data.

Automation platform  \|  Verify: [CT-043](73-appendix-d-conformance-test-catalogue.md#test_CT_043), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044), [CT-055](73-appendix-d-conformance-test-catalogue.md#test_CT_055)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_STATE_003"></a>

STATE-003  Cross-state/external-service changes SHALL use a journaled dependency workflow with scoped outputs, idempotent stage completion and data-safe compensation; state-file restoration SHALL NOT be represented as infrastructure rollback.

Automation platform  \|  Verify: [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044), [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](42-terraform-roots-adapters-and-reproducible-inputs.md) · [Chapter index](README.md) · [Next chapter](44-ci-cd-signed-plans-and-supply-chain-integrity.md)
