# Next work — begin P00

Active branch: `greenfield/enterprise-microservices-plan`.

The requested planning delivery is complete when these documents are committed and checked. Product implementation is **not started**. Use the [phased plan](docs/implementation/phased-plan.md) as the delivery sequence and [progress](docs/implementation/progress.md) as the evidence-backed status record.

## Ordered implementation backlog

| Order | Package | Concrete next task | Completion evidence |
| --- | --- | --- | --- |
| 1 | P00.01 | Confirm first application journey, personas, release scope, mandatory versus deferred platform capabilities and named owners | Product brief with explicit scope and acceptance outcomes |
| 2 | P00.02 | Create domain examples and cardinality rules for Tenant, WSD, SecurityDomain, DomainInstance, Application and Workload | Reviewed glossary, entity relationships and invariant cases |
| 3 | P00.02 | Specify ownership for intent, observation, plan, approval, admission, workflow history, native operation and evidence | Context/authority matrix with no competing writers |
| 4 | P00.03 | Resolve the requested PHP/Node/frontend/Python dependency set in an isolated compatibility spike | Exact locks, container versions, build/typecheck/test results and browser constraints |
| 5 | P00.03 | Select event transport, identity, secrets/PKI, PostgreSQL isolation, object storage and central/site runtime | Resolved ADRs with alternatives and operating owners |
| 6 | P00.04 | Select OpenStack and VMware lab tuples, one Linux image, stateful application and proposed cold migration method | Feasibility report including disk/boot/driver/consistency constraints and access readiness |
| 7 | P00.04 | Specify the lab-only qualification admission lane and production support gate | Permission/credential separation, campaign scope and negative tests |
| 8 | P00.05 | Set load tiers, discovery freshness, SLO/RPO/RTO, outage budget, retention, sovereignty and threat model | Owner-approved testable targets and trust/data flow register |
| 9 | P00.06 | Break P01 into small contract, skeleton, CI, deployment and operating-control changes | Ordered issue/commit-sized backlog mapped to R01–R36 |
| 10 | P00 gate | Review unresolved decisions and external dependencies; record accepted baseline and evidence | Gate record with owners, evidence and explicit blockers |
| 11 | P01.01–P01.06 | Build independent service skeletons and the delivery/runtime foundation | Clean-checkout build, contract checks, empty-environment install and initial restore |

## Working rules

- Start from this clean branch. Do not resume or copy the abandoned Laravel foundation's unfinished implementation.
- Use older code and documents only to understand requirements and edge cases. Reimplement against the new domain and contracts.
- Keep schema definitions and domain ownership explicit before implementing API handlers.
- No application feature, Terraform apply or native mutation is authorized merely by the existence of this plan. Future implementation work follows its environment and execution gates.
- Record lab access or owner decisions as concrete blockers while continuing independent authorized work. Do not invent credentials, approvals or successful tests.
- Keep commits small and coherent; use the GitHub connector to publish changes, consistent with the existing delivery workflow.
- Update the phase progress, requirements coverage, ADRs and current next work whenever behavior or scope changes.
