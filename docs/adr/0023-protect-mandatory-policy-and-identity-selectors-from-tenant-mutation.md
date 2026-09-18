# ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation

**Status:** Proposed<br>
**Accountable role:** Platform engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `RD14-03`<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §18](../architecture/reference/18-openstack-hosting-stack-reference-realization.md) · [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [PBS §7](../engineering/platform-build/7-openstack-protect-mandatory-network-mutation.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Tenant-editable selectors, additive security groups, port-security changes or extra attachments can widen the effective policy even when a baseline rule exists.

## Decision

Keep provider mutation authority over the mandatory network/policy/attachment envelope for the base service. Permit declared self-service through accepted workflows rather than unrestricted native edits.

## Alternatives and source limitations

Direct delegation is a separately qualified service extension whose permissions cannot expand the mandatory envelope. An additive allow mechanism must not be described as a deny hierarchy.

## Consequences

Administrative tenancy and effective network enforcement are separate. Same-host and same-subnet traffic needs enforcement even when no physical edge is traversed.

## Engineering and implementation obligations

Test selector changes, default rules, additional groups, address pairs, NICs and external-network permissions. Prove policy persists through relocation and supported lifecycle changes.

## Requirement and code traceability

[MICRO-001](../assurance/requirements.md#MICRO-001) · [MICRO-002](../assurance/requirements.md#MICRO-002) · [MICRO-003](../assurance/requirements.md#MICRO-003) · [OS-001](../assurance/requirements.md#OS-001) · [OS-002](../assurance/requirements.md#OS-002) · [NSX-001](../assurance/requirements.md#NSX-001) · [NUT-003](../assurance/requirements.md#NUT-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Native RBAC/API policy and the real immutable baseline need platform qualification; the source modules do not prove that tenant operators cannot bypass them.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
