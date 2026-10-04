# ADR-017 — Service and application objectives

Owner role: Product/SRE leads. Related phases: P00, P06, P08. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Enterprise acceptance requires measurable workload assumptions and recovery/performance objectives. These must distinguish the product control plane from hosted application commitments. The register proposes initial targets but has not accepted numeric scale, SLO, RPO, RTO or outage values.

## Decision and scope

Workload model, scale/SLO/RPO/RTO/outage objectives and measures.

Initial checkpoint: PROVISIONAL: P00.05 / G00.05 accepts initial targets and owners.

Refinement and validation: Refine after P06 measurements; native app targets before P08; measured service acceptance at G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Workload-model-based objectives by critical path | Connects targets to tenant counts, concurrency, event volume and recoverable business outcomes. |
| One availability and recovery target for the whole system | Is easy to communicate but hides differing behavior of console, workflow, evidence and native applications. |
| Adopt infrastructure defaults as product objectives | Avoids initial target work but does not establish end-to-end behavior or an accountable service commitment. |

## Consequences

- Each objective needs a measurement definition, observation window, owner and response to a missed target.
- Migration outage and application recovery targets are declared per route and cannot be inferred from control-plane availability.

## Unresolved details and evidence needed

- Set candidate workload sizes, concurrency, latency distributions, backlog limits and recovery data-loss boundaries.
- Identify lab constraints, synthetic load assumptions and how pilot observations will refine initial targets.

## Acceptance and validation

- Review initial targets and owners at P00.05/G00.05.
- Refine targets after P06 measurements and fix the native application objectives before P08.
- At G10 compare measured results with accepted targets and disclose unmet or unmeasured objectives.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

Observed load or business criticality changes, an accepted objective is repeatedly missed, or a new migration route changes the required outage or recovery profile.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
