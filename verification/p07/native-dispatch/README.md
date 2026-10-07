# P07 durable dispatch and worker transport evidence

This E2 increment implements the separate native Temporal queue and saved-plan
worker handoff. It does not establish native OpenStack provisioning or complete P07.
The [qualification index](qualification-index.json) preserves each original ZIP,
report, source revision and independently compared hashes, including the initial
failed cancellation campaign.

At `9b01db784ce4ceac012cc98592dd96997efc6168`, the component campaign runs all 288
Lifecycle and 157 worker tests without skips and passes 18 contract, static-analysis,
build and Terraform commands. The independently installed worker package also
passes at `ad32c166da60e815c03ed3633b0a43ed7fbdb801`; all 130 source bindings,
42 command streams and 46 artifact hashes match. Those 130 inputs are unchanged
at the final revision.

The live orchestration campaign passes 43 checks and replays six actual histories:

| Boundary | Observed behavior |
| --- | --- |
| Atomic dispatch | One stable workflow after an accepted start reply is lost; no second outbox dispatch |
| Ordered progression | Five provisioning stages and separately approved retirement/release |
| Current authority | Changed configuration prevents any effect; wake cannot clear a hold |
| Uncertain effect | Prepared grant and redemption survive restart; reconciliation does not repeat acceptance |
| Cancellation | Persisted native hold, no false provider-drain claim, cancelled Temporal result |
| Saved-plan handoff | Actual worker effect TLS, Lifecycle boundary TLS and separate worker PostgreSQL journal |
| Worker isolation | Two durable claims/holds and eight events; no access to Lifecycle tables; duplicate TLS submission held |
| Replay | Single-attempt activities and six successful SDK replays; private synthetic error text absent |

The final archive retains all six complete synthetic histories. The separate
[offline replay](offline-replay.json) reads those original archive members and
passes without the disposable Temporal server. History hashes and event counts
match the hosted observations.

Native authority, saved-plan effects and provider observations in the orchestration
fixture are explicitly synthetic. The separate component campaign exercises the
actual Terraform subprocess, protected artifact and independent OpenStack readback
adapters using synthetic responses; neither campaign reaches a native platform.

The [control runbook](../../../docs/operations/runbooks/native-workflow-control.md)
describes composition. The [remaining packet](../../../docs/implementation/p07-completion-review.md)
retains current owner/caller-trust implementations, provider request fencing,
selected guest/service/traffic/retirement interfaces and native qualification work.
No production dispatcher is enabled and no G07 decision is inferred.
