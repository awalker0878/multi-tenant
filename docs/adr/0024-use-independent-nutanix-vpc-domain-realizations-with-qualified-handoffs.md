# ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §16](../architecture/reference/16-nutanix-hosting-stack-reference-realization.md) · [VND §3](../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md) · [PBS §2](../engineering/platform-build/2-nutanix-commission-the-hosting-cell.md) · [PBS §3](../engineering/platform-build/3-nutanix-realize-a-tenant-and-its-workload-domains.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual VPC attachments, full Flow/VM observation and target failover/restore evidence remain outside the current candidate integration.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
