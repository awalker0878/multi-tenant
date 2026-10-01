# Profile model

A profile is a named, reviewed, ranked option in exactly one family. Catalogs live
at `profiles/<family>/catalog.json`; the directory is the only index, so there is
no second profile list that can drift.

A catalog is a **reviewed versioned artifact**, not a code constant. It states its
own revision, the revision of every profile in it, and the portable defaults that
would otherwise have to live in Python.

Loader: `provisioner/profiles/loader.py`
Resolver: `provisioner/profiles/resolver.py`
Validation: `provisioner/profiles/validation.py`
Typed requirement fields: `provisioner/profiles/requirements.py`

## Families

`environment`, `security`, `assurance`, `availability`, `recovery`, `compute`,
`storage`, `network`, `service`, `placement`.

`placement` holds the region profiles (`east`, `west`, `public`).

## Revisions

| Field | Where | Meaning |
| --- | --- | --- |
| `version` | catalog top level | the reviewed revision of that family's catalog |
| `version` | profile entry | the reviewed revision of that profile |

A revision is a positive integer written as a JSON string. The loader refuses a
missing, non-string, zero, negative or non-integer revision with
`UNSUPPORTED_PROFILE`; there is no "unversioned" catalog and no implicit default
revision.

The ten catalog revisions must form **one ladder**: no two families may share a
revision, so the set of revisions is a single monotone reviewable sequence rather
than ten independent counters that can silently collide.

`Catalog.digest` is the canonical SHA-256 of the whole reviewed set
(`Catalog.manifest()`: every family revision, every profile revision, every default
and every request default). `Catalog.version_set()` returns the same content as a
revision map. Both are recorded on every `Resolution` and every `DesiredState`, and
the plan identity binds them — so a revision bump changes the identity of every
artifact derived from it even when no request field changed.

## Catalog-owned defaults

Every portable default is declared by the catalog that owns the family, so changing
a default is a catalog review rather than a code change. Nothing in this table is
restated in Python.

| Default | Declared by | Catalog field |
| --- | --- | --- |
| `assurance.profile` | `assurance` | `default` |
| `capacity.computeProfile` | `compute` | `default` |
| `capacity.storageProfile` | `storage` | `default` |
| `network.profile` | `network` | `default` |
| `recovery.profile` | `recovery` | `default` |
| the portable service list | `service` | `services` |
| each service's default profile | `service` | `defaults` |
| `recovery.enabled` | `recovery` | `requestDefaults` |
| `exposure.publicIngress`, `exposure.internetEgress` | `security` | `requestDefaults` |
| `zones.operations.enabled`, `zones.restricted.enabled` | `availability` | `requestDefaults` |

A default must be an **implemented** profile of its own family: the loader refuses a
default that names an unknown or deferred profile, and refuses a `services` list
declared by anything but the service catalog.

`provisioner/compiler/normalize.py` reads this table through
`normalize.defaults_for(catalog)` and is the only place a default is applied to a
request. `provisioner/profiles/resolver.py` reads the same catalog fields for the
one case where the choice is only meaningful at resolution time (a recovery profile
when `recovery.enabled` is true), so both readers share one source of truth.

## Typed fields and cross-profile obligations

One closed requirement-field owner covers all ten catalog families. Required fields
must exist; booleans are not numbers and strings/floats are not coerced into quantities.
Relationship sets are bounded, nonempty and unique. Quantities use representation
bounds, not assumed native platform maxima; address parameters must fit the selected
family and placement selectors must have an implemented resolver. Capability property
constraints retain their separate typed semantic owner.

Standalone and full request validation share assurance-required recovery. Availability
minimum workload counts must fit the compute profile, and recovery must name a selected
zone. Independent-site recovery remains explicitly unsupported rather than becoming
implemented through a renamed catalog entry. Availability catalog 18 corrects security
zone/failure-domain wording; separate domains, HA admission reserves, restart behavior
and application recovery still need observed qualification. Catalog changes regenerate
all dependent example fingerprints and require new review of proposed execution plans.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `IMPLEMENTED_INTERNAL_IPV4_OZ_RZ` | reviewed and usable by a request in this repository |
| `DEFERRED_NOT_IMPLEMENTED` | declared so the refusal is explicit; selecting it is refused |

A deferred profile is never silently downgraded to a neighbouring profile. The
refusal is `UNSUPPORTED_PROFILE` with the deferred name in the diagnostic.

## Resolution

Resolution is a pure function of the request and the catalogs:

1. Each family name is looked up. A missing name is `UNSUPPORTED_PROFILE`. A field
   the request omitted is filled from the catalog that owns the default; a service
   name the catalog does not own is refused rather than ignored.
2. A deferred name is `UNSUPPORTED_PROFILE`.
3. `requires` is followed transitively; every requirement must itself resolve and
   be implemented, otherwise the request is refused rather than partly resolved.
4. The resolved set is expanded into `required_capabilities`, `limits`,
   `platform_inputs`, `trust`, `service_class`, `lifecycle` and the numeric
   `compute`/`storage`/`network` inputs the allocator and compiler consume.
5. `validate()` checks the resolved set for internal consistency and returns a
   `Diagnostics`; it does not raise, so policy can report every refusal at once.

The result is a `Resolution` with no remaining `auto` value: `format`, `compute`,
`lifecycle`, `limits`, `network`, `platform_inputs`, `profiles`, `required_capabilities`,
`service_class`, `services`, `storage`, `trust`, `zones`, and the reviewed revision
set it resolved against — `profile_versions`, `catalog_versions`, `catalog_digest`.
The resolution format is `hosting-profile-resolution/3`.

## Rank

Every profile carries a rank inside its family. Rank is used for minimums
(`environment: production` needs availability rank ≥ `high`) and for deterministic
tie-breaking. Rank is never used to substitute one profile for another.

## Adding a profile

Add the entry to the catalog with an explicit status and `version`, raise the
catalog's own `version`, then add a regression to
`tests/provisioning/policy/test_profiles_policy.py`. A catalog entry without a
regression is not reviewed. Removing or renaming a profile is a breaking change to
the request contract and needs a note in the retired-interfaces register.

## Changing a profile

A change to any profile field is a revision, not an edit: raise the `version` of the
profile that changed and the `version` of its catalog. The golden corpus then has to
be regenerated, because a plan binds the revision set and the change is visible in
the desired state, the plan digest and the conformance report. That is the intended
cost: a reviewed policy change must be visible in review.

## Typed semantic constraints

Profiles may declare bounded `requires.constraints` beneath existing capability
IDs. Each entry contains exactly `property`, `operator` (`eq`, `gte`, `lte`) and
`value`. Enumerations and booleans accept equality only; integer inequalities do
not accept boolean or floating values. Every property must have its capability
in `requires.capabilities`. All profile constraints intersect and contradictions
fail before compilation. Resolution format 3 and the complete catalogue digest
bind the property interpretation to plans.

Placement evaluates each selected cluster's immutable `capability_properties`;
missing observations cannot be borrowed from another cluster or inferred from a
platform name. Policy capsule/realization format 2 requires destination constraints
to entail the source obligations. See the
[research decision record](../engineering/platform-migration-research.md) for types,
version changes, known limitations and qualification boundaries.
