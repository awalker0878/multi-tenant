# Phase work packages

This directory expands the [programme sequence](../phased-plan.md) into implementation tasks. Each phase names accountable roles, prerequisites, concrete outputs and measurable checks. The [delivery register](../delivery-register.yaml) remains authoritative for progress, evidence and gate decisions.

| Phase | Outcome | Entry dependency |
| --- | --- | --- |
| [P00](p00.md) | Product and architecture baseline | Planning baseline |
| [P01](p01.md) | Delivery and runtime foundation | P00 |
| [P02](p02.md) | Identity, tenancy and governance | P01 |
| [P03](p03.md) | Application catalogue and workspace | P01, P02 |
| [P04](p04.md) | Site commissioning and inventory | P01, P02 |
| [P05](p05.md) | Capabilities and immutable plans | P03, P04 |
| [P06](p06.md) | Durable execution in simulation | P02, P05 |
| [P07](p07.md) | Native OpenStack provisioning | P06 |
| [P08](p08.md) | VMware-to-OpenStack migration | P07 |
| [P09](p09.md) | Platform and capability expansion | P05, P06, P07, P08 |
| [P10](p10.md) | Enterprise operating qualification | P08, P09 |
| [P11](p11.md) | Pilot and supported release | P10 |

## How to maintain phase detail

1. Confirm current requirement, decision and contract ownership before starting a package. Refine effort against named staffing and external-access assumptions.
2. Keep package IDs stable; add implementation tasks under the package rather than renumbering canonical requirements or gates. Use the [work-package template](../../templates/work-package.md).
3. Add concrete output locations as implementation boundaries settle. Update the owning specification in the same change, then record actual test and review evidence in the canonical register.
4. Review each [gate criterion](../gates.md) separately using its [review procedure](../../qualification/gate-reviews/README.md); discovery, simulation, native qualification and operational acceptance retain their distinct evidence levels.
5. Capture any changed scope or blocked dependency with accountable owner and unblock condition. Regenerate derived views and update `next_work.md` after an accepted decision.

P02–P04 may overlap when contracts are stable. P09 is assessed per selected tranche. P10 engineering starts in P01, while its final review covers every capability included in the release. See [status rules](../status-model.md) and [documentation ownership](../../documentation-guide.md) for cross-document updates.
