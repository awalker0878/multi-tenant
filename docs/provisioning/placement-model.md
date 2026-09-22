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
| `HOLD_PLATFORM_NOT_QUALIFIED` | every candidate was rejected because its platform is not natively qualified for the required capabilities |
| `HOLD_NO_ELIGIBLE_PLATFORM` | a candidate was rejected for residency or another reason with no more specific class |
| `HOLD_NO_ELIGIBLE_SITE` | no candidate was evaluated at all (region, platform or pin matched nothing) |

A decision carries exactly one status. When several candidates were rejected, the
status is the first matching class in the order above; every individual reason is
still recorded per candidate in `candidates[].blockers` and in `reasons`.

Each candidate also records the class of every blocker it hit, so a specific,
actionable failure stays distinguishable from a platform-wide gap:

| Field | Content |
| --- | --- |
| `blocker_classes` | one of `residency`, `capability`, `capacity`, `prefix-pool`, `service`, `qualification` |
| `qualification_blockers` | why the candidate's platform is not natively qualified |
| `cell_blockers` | the required capabilities the selected cell cannot carry |
| `product_tuple` | the product tuple the candidate was evaluated against |

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

`PlacementDecision.authorized` is true only when the status is `PLACED`, the
inventory authority is `AUTHORITATIVE_SITE_STATE` **and** the recorded
qualification is authoritative. A decision assembled without a recorded
qualification records the explicit identity `UNRECORDED`/`NOT_EVALUATED` and is
never authorized.

## Determinism

Candidates are ordered by score, then by the stable key (site, cell, platform), so
the same request over the same inventory always selects the same target and yields
the same digest. Two different requests never share a placement digest.

## Native qualification

Native qualification is a **mandatory** eligibility filter, not a note on an
otherwise eligible candidate. A platform whose required capabilities are not
natively qualified can never produce a `PLACED` decision, however attractive its
score is; the candidate is rejected with the `qualification` blocker class and the
decision holds with `HOLD_PLATFORM_NOT_QUALIFIED` when no other candidate
survives. Qualification blockers and cell-capability blockers stay distinct, so a
hold always says whether the platform or the cell was the problem.

Two qualification sources exist and are deliberately not interchangeable:

| Source | `source` | Authoritative | Reads |
| --- | --- | --- | --- |
| `RepositoryQualification` | `repository-capability-registry` | yes | `sources/capabilities/platform_registry.json` |
| `DeclaredQualification` | `declared:<name>` | no | `provisioner/inventory/fixtures/demonstration-qualification.json` |

* The reviewed registry is the default and the **only** source an authoritative
  inventory may be planned against. `place()` refuses the combination of an
  authoritative inventory with a non-authoritative source.
* The declaration is a machine-recorded assumption, status
  `DECLARED_NOT_NATIVE_QUALIFICATION`, that exists so the reviewed fixture corpus
  can still exercise the pipeline. It is not evidence, its product tuples are
  named `DECLARED-DEMONSTRATION-TUPLE-NOT-NATIVE-EVIDENCE`, and every decision
  resting on it records the declaration and adds the limit
  *"Native qualification is absent; this decision rests on a declared
  qualification assumption"*.

The registry currently qualifies nothing: every product tuple is `UNSELECTED`,
every capability claim is `NOT_QUALIFIED` and no claim carries a
`native_evidence_ref`. So an authoritative inventory always holds with
`HOLD_PLATFORM_NOT_QUALIFIED`, and that is the correct, recorded outcome —
placement must not invent external qualification. The decision records the source,
its status, whether it was authoritative and the product tuple of every platform
it evaluated in `qualification` and `qualification_blockers`.

## Pins

`placement.site` and `placement.cell` narrow the candidate set; they do not bypass
eligibility, capacity, capability or service checks. A pinned target that fails any
check produces a hold, not a forced selection.