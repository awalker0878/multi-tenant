# Product decision — Select Temporal for the workflow authority, conditional on self-hosted qualification

**Status:** Proposed engine selection; local SDK spike passed, production deployment not qualified  
**Decision class:** B08 technical decision, organizational acceptance pending  
**Date:** 2026-09-27  
**Scope:** Long-running provisioning and migration orchestration in the approved management environment

## Context and decision

The enterprise product needs timers, operator waits, replay after worker loss, and a single job resumption authority. Local SQLite journals and process locks protect individual operations but are not a distributed multiuser workflow engine. Select **self-hosted Temporal** as the one proposed workflow authority. Run its server and durable persistence inside the approved management boundary; deploy control-plane workers and site-local activity workers only where their network and credentials are authorized. Keep the product database authoritative for identities, grants, native-operation intents, ownership epochs and audit facts. A Temporal event history is authoritative for workflow progress, timers and resumption, not for whether a hypervisor or guest actually changed.

This selection is conditional. The present code is an approval gate spike, not a provisioning or migration workflow. It never executes a native action. Temporal Cloud, a local test server, or a second local job runner must not silently become the production authority.

Temporal's current [self-hosted deployment guide](https://docs.temporal.io/self-hosted-guide/deployment) describes server binaries, containers and Helm deployment; it warns that server hosts should be restricted to trusted internal networks. The [security guide](https://docs.temporal.io/self-hosted-guide/security) documents opt-in internode/frontend mTLS and authorization extensions. The [Python workflow guide](https://docs.temporal.io/develop/python/workflows/versioning) requires replay-safe code and moves I/O into Activities. [Worker Versioning](https://docs.temporal.io/production-deployment/worker-deployments/worker-versioning) currently requires self-hosted Server >=1.29.1 and Python SDK >=1.11, and recommends pinned worker deployments where operationally feasible. Those version facts must be rechecked when deployment versions are chosen.

## Spike evidence

`provisioner/controlplane/workflow/approval_gate.py` has a bounded durable wait for an opaque approval notice. A Signal merely prompts an Activity to ask the future B07 authority for a current decision bound to organization, tenant, exact plan revision/digest and approval ID. An invalid signal, failed check or malformed proof holds; an expired timer stops; a passing result only reports `GATE_PASSED`. No approval JSON from a caller is trusted and no native effect follows the result.

`tests/provisioning/workflow/test_approval_gate.py` ran with Temporal Python SDK 1.33.0 in an isolated environment:

| Check | Observed result | Limit |
| --- | --- | --- |
| Approval wait and timer | SDK time-skipping test server advanced an hour; the gate expired without invoking the Activity | Test server memory is not production storage |
| Worker loss and resumption | Local Temporal development server retained a pending execution; first worker stopped, a notice was signaled while no worker ran, and a second worker completed the gate | Server and database process were not killed or restored |
| Deterministic replay | Fetched the completed history and replayed it with the current Workflow definition | No history from an older production build exists |
| Scope and authority binding | Wrong-tenant notice never reached the Activity; malformed evidence caused a hold | B07 authentication, revocation and separation of duties are not implemented |
| Worker upgrade | A new worker process resumed the same Workflow code | Changed Workflow definitions, deployment pinning and actual server Worker Versioning were not tested |
| Restricted network | The local development server used loopback | Air-gapped image supply, mTLS, authorization, firewall, DNS, data residency and no-egress operation remain untested |

The test server emitted a capability warning about preserving heartbeat details after Activity failure. The spike has no long-running native Activity and does not claim to qualify that behavior. A matched production Server/SDK combination must prove heartbeats and retry semantics before native actions are enabled.

## Production deployment boundary

1. Provide an approved, privately addressed Temporal cluster with an independently operated persistence database and visibility store. Restrict the Frontend to trusted control and site-worker networks. Mirror and verify server, UI, admin tools and SDK artifacts within the restricted environment; pin compatible versions, schema migrations and upgrade order. Do not expose the Web UI or Frontend to an untrusted network.
2. Require TLS/mTLS between Temporal services and clients, client/server identity verification and an explicit authorization policy for namespaces, history, Signal and Update APIs. A task queue is scheduling, not tenant access control. Use separate worker credentials and network paths by site/security domain where needed; the product rechecks each business authorization inside an Activity.
3. Limit workflow payloads and history to stable IDs, digests and non-secret receipts. Keep credentials, full plans, workload bytes and sensitive evidence outside history. Apply retention and encryption controls to server persistence, backups, visibility and any payload codec; test restoration without broadening access.
4. Submit a stable job ID as Temporal Workflow ID through the B09 transactional outbox, with duplicate-start acknowledgement only after the existing run's tenant/plan binding is verified. Implement B10 worker enrollment, fenced native-operation intents and B11 observe-before-retry in Activities; Temporal's at-least-once Activity execution is not native idempotency.
5. Qualify Server >=1.29.1 with a pinned Python SDK and Worker Versioning in a restricted-network lab. Use a controlled multi-version rollout for long-lived histories or documented replay-safe patches. Store representative open/closed histories and fail CI when the next Worker cannot replay them. Keep old pinned Workers until their executions drain; this is deployment lifecycle, not a runtime compatibility shim.
6. Prove server/worker crash, lost response, network partition, PostgreSQL backup/restore, concurrent Signals, timer recovery, upgrade/rollback and failover. Reconcile every in-flight native task on recovery. Declare recovery targets and an operator owner before calling B08 production-qualified.

The operational qualification is a **blocking gate**. Until it passes, this module is a tested Temporal integration spike only; B09 must not treat a gate result or the local test environment as permission to provision or migrate a workload.

[Product state ownership](state-ownership.md) · [Implementation plan](../enterprise-workload-mobility-audit-and-implementation-plan.md)
