# Gate reviews

A gate review evaluates the evidence for a bounded phase scope against the [canonical criteria](../../implementation/gates.md). These procedures define how reviewers examine that evidence. Actual decisions, reviewer identities, dates, evidence IDs and blockers are maintained in the [delivery register](../../implementation/delivery-register.yaml) under the [status rules](../../implementation/status-model.md).

## Review sequence

1. Freeze the phase scope and source/release/artifact revisions. Confirm the [phase entry dependencies](../../implementation/phased-plan.md) and identify the requirement/package scope being reviewed.
2. Assemble immutable evidence per criterion, including positive, negative and recovery cases. Verify digests, environment, observer independence, exact native tuple where required and any validity/retest conditions.
3. Apply the corresponding procedure below. Compare actual observations to the required outcome; missing evidence is not a pass and a test design is not an execution result.
4. Record each criterion's assessment, limitations and blockers in a protected immutable review record. Link that record into the register; retain prior review history.
5. Record the resulting gate decision in the register and regenerate derived progress/traceability. A gate review does not itself authorize unrelated native or production changes.

## Review procedures

| Gate | Procedure | Main evidence boundary |
| --- | --- | --- |
| G00 | [Product and architecture baseline](g00.md) | Reviewed design and actual bounded feasibility/compatibility experiments |
| G01 | [Delivery and runtime foundation](g01.md) | Clean builds and isolated real-dependency integration |
| G02 | [Identity, tenancy and governance](g02.md) | Negative authority, isolation and approval behavior |
| G03 | [Application catalogue and workspace](g03.md) | Domain invariants, persistence and operator task outcomes |
| G04 | [Site commissioning and inventory](g04.md) | Native read-only coverage, completeness and ownership safeguards |
| G05 | [Capabilities and immutable plans](g05.md) | Reproducible findings, bound authority and reservation handling |
| G06 | [Durable execution in simulation](g06.md) | Integrated fault/recovery and custody behavior |
| G07 | [Native OpenStack provisioning](g07.md) | Exact-tuple application/service/policy and retirement outcomes |
| G08 | [VMware-to-OpenStack migration](g08.md) | Ordered fencing, data correctness and both recovery boundaries |
| G09 | [Platform and capability expansion](g09.md) | Separate qualification for every selected tranche row |
| G10 | [Enterprise operating qualification](g10.md) | Release-bound resilience, recovery, security and support acceptance |
| G11 | [Pilot and supported release](g11.md) | Approved pilot outcomes and independent operational handover |

## Review controls

The reviewer role for each criterion is defined in the canonical gate specification; assign actual people during the review. Document conflicts or missing independence. Do not use a role label as a fabricated signatory or backfill an unobserved execution date.

Distinguish work completion, verification, native qualification and operational acceptance. A passed design gate does not imply native support; a native campaign does not grant production permission. G09 is reviewed per selected tranche, while G10 includes every tuple advertised for the release.

Preserve failed and absent evidence with its remedial work and unblock condition. If scope is narrowed, update the requirement/package mapping, support claim and affected procedures before reevaluation. Material artifact, tuple, topology, policy, method or recovery changes reopen the affected review; evidence reuse requires an explicit impact decision.
