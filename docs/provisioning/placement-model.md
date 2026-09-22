# Placement model

Placement turns a resolved request into either one deterministic site/cell/platform
selection or an explicit hold. It is **fail-closed**: a hold is a valid, recorded
outcome, and nothing downstream may substitute a site.

Modules: `provisioner/placement/eligibility.py`, `provisioner/placement/resolver.py`
Model: `provisioner/domain/placement.py`
Inventory: `provisioner/inventory/model.py`, `provisioner/inventory/capacity.py`

## Inputs

* the resolved request (region, platform preference, zone count, trust, service
  class, required capabilities, service profiles, prefix length, optional site/cell pin)
* the reviewed inventory: sites, regions, cells, clusters, capacity, service endpoints

## Output

A `PlacementDecision` (`hosting-placement-decision/1`) that records **every**
candidate it evaluated — eligible or not — with its score and the exact blockers:

| Status | Meaning |
| --- | --- |
| `PLACED` | one candidate selected |
| `HOLD_CAPACITY_INSUFFICIENT` | a candidate was rejected because the cluster cannot host the declared demand |
| `HOLD_SERVICE_UNAVAILABLE` | a candidate was rejected because a required service endpoint or binding class is absent |
| `HOLD_PREFIX_POOL_EXHAUSTED` | a candidate was rejected because no prefix of the resolved length remains |
| `HOLD_CAPABILITY_NOT_QUALIFIED` | a candidate was rejected because the cell lacks a required capability |
| `HOLD_NO_ELIGIBLE_PLATFORM` | a candidate was rejected for residency or another reason with no more specific class |
| `HOLD_NO_ELIGIBLE_SITE` | no candidate was evaluated at all (region, platform or pin matched nothing) |

A decision carries exactly one status. When several candidates were rejected, the
status is the first matching class in the order above; every individual reason is
still recorded per candidate in `candidates[].blockers` and in `reasons`.

## Authority

| Authority | Meaning |
| --- | --- |
| `AUTHORITATIVE_SITE_STATE` | reviewed site state; a `PLACED` decision may be planned |
| `FIXTURE_NOT_PLACEMENT_AUTHORITY` | non-authoritative input; cannot be promoted |

The repository currently ships three fixtures
(`provisioner/inventory/fixtures/openstack-reference.json`,
`nutanix-reference.json`, `vmware-reference.json`). Their decisions are
therefore `FIXTURE_NOT_PLACEMENT_AUTHORITY`, and `PlacementDecision.authorized` is
`False` even when the status is `PLACED`. `create_plan` accepts a fixture-derived
selection so the pipeline can be exercised, but no artifact claims authorization.

## Determinism

Candidates are ordered by score, then by the stable key (site, cell, platform), so
the same request over the same inventory always selects the same target and yields
the same digest. Two different requests never share a placement digest.

## Product tuples

`eligibility.product_tuple(platform)` resolves the reviewed product tuple for a
platform. The registry currently has **no** qualified tuple, so every platform gate
reports blockers. Those blockers are recorded per candidate in
`candidates[].capability_blockers` and at decision level in `registry_blockers`;
they are *not* a cell-capability failure, so they do not by themselves produce a
`HOLD_CAPABILITY_NOT_QUALIFIED`. This is intentional: native qualification is
external evidence, and placement must not invent it.

## Pins

`placement.site` and `placement.cell` narrow the candidate set; they do not bypass
eligibility, capacity, capability or service checks. A pinned target that fails any
check produces a hold, not a forced selection.