# ADR-016 — Terraform plans and resource ownership

Owner role: Infrastructure lead. Related phases: P00, P05, P06, P07. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Infrastructure execution must apply the reviewed resource change and prevent overlapping ownership between Terraform, direct provider APIs and other tools. The proposed baseline uses reviewed saved plans with explicit resource/field ownership. Tool versions, backend, workspace structure and lock behavior are deployment inputs: discover them through owner APIs where available and collect remaining choices and evidence references through Console administration. These inputs bind native execution and qualification without blocking independent product development.

## Decision and scope

Reviewed Terraform saved plan and explicit resource/field ownership; tool/backend versions unresolved.

Initial checkpoint: LATER: assign owner in P00; select before P05.04 plan model.

Refinement and validation: Lock backend/workspace/ownership and toolchain before P06.03/P07.02; qualify uncertainty/recovery at G07.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Saved plan bound to approved intent and ownership | Supports review of a concrete change while requiring artifact integrity, state binding and freshness checks. |
| Re-plan automatically at apply time | May adapt to drift but can change the approved effect; a changed plan must return through approval. |
| Direct API ownership for all resources | Avoids Terraform state for those resources but transfers planning, locking, reconciliation and recovery responsibilities to adapters. |

## Consequences

- An ownership map identifies the sole writer for every managed resource or field and handles externally owned resources explicitly.
- State, plans and credentials require protected storage; uncertain apply outcomes require reconciliation before retry.

## Unresolved details and evidence needed

- Select tool/provider versions, backend/workspace boundaries, locking and state recovery ownership.
- Define plan digests, approval binding, expiry, drift invalidation and adoption/import behavior.

## Acceptance and validation

- Finalize the immutable plan model before P05.04 implementation depends on it.
- Verify locks, ownership denial and immediate authority rechecks before P06.03/P07.02.
- Qualify interrupted applies, drift, partial effects and recovery at G07.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A provider or backend change alters planning/apply behavior, resource ownership moves between tools, or drift invalidates the approval model.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.

## P05 engineering representation — 2026-10-06

The authorized P05 implementation selects the saved-plan representation above:
exact saved-plan/toolchain hashes, backend/workspace, state lineage and serial,
lock owner, and sole writer per managed field. The compiler rejects overlapping
writers and holds missing state/ownership rather than substituting an unreviewed
apply-time plan. This is the concrete engineering choice before P05.04 compilation;
it does not appoint a receiving owner or claim acceptance of a native backend.
Actual native tool/provider/backend selections and independent state recovery
qualification remain due at P06.03/P07.02. See the [P05 record](../implementation/p05-planning.md).

## P07 preparation representation — 2026-10-06

The [P07 implementation](../implementation/p07-native-provisioning.md) compares
the existing P05 saved-plan byte hash with a versioned, exactly pinned toolchain
manifest and supplied state/lock/ownership observations. Its protected commissioning
packet binds those identities to the exact plan, site, tuple, resource scope and
campaign. Unknown effects and mismatches remain held. These are offline comparison
contracts; they do not authenticate owners, select a native provider/backend,
enforce its lock, or issue a grant. Actual tool-byte verification, state custody,
fencing and native readback remain part of the selected P07.02 integration. This
refinement does not change the decision register's receiving disposition.

## P07 adapter component increment — 2026-10-07

The [worker components](../operations/runbooks/openstack-native-adapters.md) now
verify actual protected executable, provider, module and saved-plan bytes; compare
workspace/state lineage/serial; invoke only the reviewed saved plan with locking;
and independently read exact OpenStack object IDs. Durable PostgreSQL claims
exclude a second launch on the same held state lineage. Initial plans admit only
owned, quarantined creates. The installed command remains read-only.

The [E2 component evidence](../../verification/p07/native-components/qualification-index.json)
does not establish native lock custody or provider fencing. Product native grant
redemption, exclusion of stale provider requests and independently reconciled
recovery remain required before dispatch. Actual backend/tool selections remain
Console-managed commissioning inputs under the existing baseline. No new baseline
decision, native support claim or receiving disposition is introduced.
