# ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) · [PBS §2](../engineering/platform-build/2-nutanix-commission-the-hosting-cell.md) · [PBS §3](../engineering/platform-build/3-nutanix-realize-a-tenant-and-its-workload-domains.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Generally routed OZ and RZ networks inside one VPC can communicate without the diagrammed external inspection hop.

## Decision recorded in the source

Realize independent domain instances with separate VPC or equivalently qualified routing contexts. Keep project/RBAC, protected categories and external handoff controls distinct. Prefer routed no-NAT internal handoff where the actual stack supports its required isolation and source identity.

## Alternatives and limits recorded in the source

NAT can support an explicit overlap or service need. Shared external subnets require separate qualification; otherwise use isolated attachment capacity.

## Consequences

Prism/Flow readiness and AOS/controller/storage sharing remain real dependencies. A v2/v4 resource name alone does not establish platform compatibility or complete operation coverage.

## Engineering and implementation obligations

Record exact AOS/Prism/Flow/provider releases, entitlement, host/storage scope, external-subnet behaviour, route symmetry and create/update/delete completion.

## Requirement and code traceability

[NUT-001](../assurance/requirements.md#NUT-001) · [NUT-002](../assurance/requirements.md#NUT-002) · [NUT-003](../assurance/requirements.md#NUT-003) · [NUT-004](../assurance/requirements.md#NUT-004)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual VPC attachments, full Flow/VM observation and target failover/restore evidence remain outside the current candidate integration.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
