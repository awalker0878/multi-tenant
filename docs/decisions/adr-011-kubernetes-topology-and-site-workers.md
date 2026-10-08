# ADR-011 — Kubernetes topology and site workers

Owner role: SRE/security leads. Related phases: P00, P01, P04. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The deployment proposal places central services in Kubernetes within each accepted trust boundary and uses scoped workers for site access. A cluster boundary alone does not define tenant authorization or permitted network flows. Distribution, CNI, worker placement and bootstrap choices are still proposed or unresolved.

## Decision and scope

Central Kubernetes per accepted trust boundary; scoped site workers; runtime/CNI/flows unresolved.

Initial checkpoint: NOW: P00.03 distribution/initial topology before P01.02.

Refinement and validation: Site trust/network scope before P04.01; native write readiness before G07.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Central Kubernetes and scoped site workers | Centralizes the product control plane while localizing native connectivity and worker authority. |
| Complete product installation at each site | Reduces central connectivity dependence but multiplies upgrades, governance and evidence reconciliation. |
| Central workers with broad site reach | Simplifies placement but expands network exposure and must be justified against explicit least-scope requirements. |

## Consequences

- The deployment model must enumerate central dependencies, site connections and worker registration/expiry behavior.
- Namespace, node and network isolation are implementation controls; accepted trust boundaries may require separate clusters.

## Unresolved details and evidence needed

- Choose distribution/runtime, CNI and ingress/egress design, and document required flow owners.
- Determine worker placement, enrollment, certificate rotation and action during disconnection.

## Acceptance and validation

- Install the initial topology reproducibly before P01.02 completion.
- Validate blocked unauthorized flows and constrained site worker permissions before native readiness.
- Confirm site trust and network scope in P04.01 and native write readiness before G07.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A site or tenant trust requirement demands stronger physical separation, cluster operation is unsupported, or network restrictions invalidate central dependency assumptions.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
