# ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs

**Status:** Proposed<br>
**Accountable role:** Platform engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) · [PBS §2](../engineering/platform-build/2-nutanix-commission-the-hosting-cell.md) · [PBS §3](../engineering/platform-build/3-nutanix-realize-a-tenant-and-its-workload-domains.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Generally routed OZ and RZ networks inside one VPC can communicate without the diagrammed external inspection hop.

## Decision

Realize independent domain instances with separate VPC or equivalently qualified routing contexts. Keep project/RBAC, protected categories and external handoff controls distinct. Prefer routed no-NAT internal handoff where the actual stack supports its required isolation and source identity.

## Alternatives and source limitations

NAT can support an explicit overlap or service need. Shared external subnets require separate qualification; otherwise use isolated attachment capacity.

## Consequences

Prism/Flow readiness and AOS/controller/storage sharing remain real dependencies. A v2/v4 resource name alone does not establish platform compatibility or complete operation coverage.

## Engineering and implementation obligations

Record exact AOS/Prism/Flow/provider releases, entitlement, host/storage scope, external-subnet behaviour, route symmetry and create/update/delete completion.

## Requirement and code traceability

[NUT-001](../assurance/requirements.md#NUT-001) · [NUT-002](../assurance/requirements.md#NUT-002) · [NUT-003](../assurance/requirements.md#NUT-003) · [NUT-004](../assurance/requirements.md#NUT-004)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual VPC attachments, full Flow/VM observation and target failover/restore evidence remain outside the current candidate integration.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
