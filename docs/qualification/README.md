# Qualification and acceptance

Qualification establishes what this product can safely do on a specific deployment, with a specific application and a specific release. This section supplies repeatable assessment procedures. Actual observations, evidence references, blockers and decisions belong in the [delivery register](../implementation/delivery-register.yaml); document existence never establishes a passing result.

## How to use this section

1. Select the requirement, operation and release scope from the [requirements baseline](../implementation/requirements-and-qualification.md) and [support matrix](../implementation/support-matrix.md).
2. Establish feasibility and an exact qualification tuple before committing to native implementation or advertising a route.
3. Create a run manifest for each execution of the applicable campaigns. Keep synthetic, native laboratory and operational evidence distinguishable throughout collection and review.
4. Execute positive, negative and recovery cases. Preserve failures and interrupted runs; do not discard them when retrying.
5. Review the evidence against each applicable [gate criterion](../implementation/gates.md). Record actual decisions through the [gate review process](gate-reviews/README.md).
6. Publish a support claim only for the independently reviewed tuple and release; reopen affected reviews after a material change.

## Procedures

| Procedure | Purpose | First use |
| --- | --- | --- |
| [Initial route feasibility](feasibility/initial-route.md) | Establish the candidate VMware-to-OpenStack method, constraints and recovery boundaries | P00.04 / G00.04 |
| [Q01 — Contract and tenancy](campaigns/q01-contract-and-tenancy.md) | Cross-language behavior, tenant boundaries and immutable catalogue intent | P01–P03 |
| [Q02 — Discovery and adoption](campaigns/q02-discovery-and-adoption.md) | Complete read-only observations and separately authorized ownership transfer | P04; P09 adoption |
| [Q03 — Planning and authority](campaigns/q03-planning-and-authority.md) | Explainable eligibility, immutable plans, approvals and reservation races | P05–P06 |
| [Q04 — Durable execution](campaigns/q04-durable-execution.md) | Unknown outcomes, fencing, retries, recovery and evidence custody | P06; native reruns in P07 |
| [Q05 — Native provisioning](campaigns/q05-native-provisioning.md) | OpenStack application creation, service readiness, activation and retirement | P07 |
| [Q06 — Policy equivalence](campaigns/q06-policy-equivalence.md) | Required and denied traffic outcomes across the actual topology | P07; each relevant P09 tuple |
| [Q07 — First offline migration](campaigns/q07-first-offline-migration.md) | VMware-to-OpenStack data correctness, fencing and both recovery boundaries | P08 |
| [Q08 — Route expansion](campaigns/q08-route-expansion.md) | Independently qualify additional directions, methods, guests and adoption | P09 |
| [Q09 — Deployment and recovery](campaigns/q09-deployment-and-recovery.md) | Installation, trust, upgrade and coordinated control-plane recovery | P01 baseline; P10 qualification |
| [Q10 — Scale and pilot](campaigns/q10-scale-and-pilot.md) | Measured operating limits and receiving-team acceptance | P10–P11 |
| [G00–G11 reviews](gate-reviews/README.md) | Assess evidence and close a bounded phase scope | Every phase |

## Run manifest and evidence custody

Each run receives a distinct run ID under its Q-series campaign. Record product source revision, image and dependency digests, contract/profile versions, environment identity, test case IDs, fixture seed and manifest digest, timestamps, authorization reference, observer and independent reviewer. Native runs also identify the exact source/target tuple, direction, method, guest, data, policy, service, topology and assurance profiles. Preserve protected endpoint and credential references without exposing their values in Git.

Record the precondition observations, requested action, injected fault, authoritative readback, expected-versus-observed comparison, cleanup disposition and limitations for every case. Evidence objects must meet the complete metadata requirements in the [status model](../implementation/status-model.md#evidence-levels), including immutable artifact URI, SHA-256, source/artifact revisions, scope, criterion IDs, observation/review identities and validity rules. E0–E4 classifications apply to individual evidence items, not to how polished the report looks.

## Controls shared by all campaigns

- Use the synthetic [Permit Desk](../product/application-walkthrough.md) data and a second tenant for isolation checks. Reproducible fixtures must contain no copied production data or credentials.
- Reconcile owned resources and allocation receipts before and after each run. Cleanup requires its own authorized scope and must respect retention or unresolved outcomes.
- Inject native faults only within the approved laboratory impact boundary. A procedure authorizes no mutation by itself.
- Stop the affected scope when a writer cannot be fenced, an outcome cannot be determined, custody is uncertain or a test exceeds its budget. Retain evidence and escalate through the named run owner.
- A skipped or unavailable required case remains missing evidence. Resolve the dependency, narrow the supported scope through review or leave the gate open.

## Maintaining the procedures

Keep stable case IDs when refining a test; add a new ID for a materially different behavior and explain supersession in the run history. Update the campaign, affected service/contract specification and requirement links together. A change to adapters, native versions, enforcement topology, migration method, guest image, recovery procedure or operating objective triggers an impact review identifying cases to rerun and evidence that can demonstrably be reused. Current execution state remains in one register.
