# Active contract catalogue

This directory is the **current wire/data contract surface**, not an archive or an
execution-authority engine. Older releases are available in Git history, not as
working-tree compatibility artifacts.

## Canonical ownership

- `architecture/contract-consumers.json` lists every current canonical release,
  owner, consumer, installed package copy, source manifest and dependency.
- `architecture/retired-contract-releases.json` records removed paths and per-path
  decisions. The external-consumer statuses distinguish repository evidence from
  independently established external compatibility commitments.
- `contracts/openapi/`, `contracts/asyncapi/`, `contracts/schemas/`,
  `contracts/capabilities/` and `contracts/platforms/` contain active bundles.
- `contracts/source/` is the editable split authoring representation for larger
  assembled contracts; `contracts/fixtures/` contains only test cases.
- A new breaking wire contract receives a new version. Current existing releases
  are byte-frozen relative to the review base. Historical-only aliases, shims,
  replay fixtures and packaged consumer copies are not preserved.

## Installed consumers

| Interface | Active canonical artifact | Installed runtime |
| --- | --- | --- |
| Catalogue HTTP | `openapi/catalogue-v1.0.1.json` | Console |
| Inventory HTTP | `openapi/inventory-v1.9.json` | Console |
| Planning HTTP | `openapi/planning-v1.2.json` | Console |
| Planning migration | `openapi/planning-migration-v1.6.json` | Console |
| Lifecycle native jobs | `openapi/lifecycle-native-jobs-v1.1.json` | Console |
| Inventory planning input | `schemas/planning/inventory-input-v2.json` | Planning |
| Inventory migration input | `schemas/planning/migration-input-v4.json` | Planning |
| Qualification | `schemas/planning/qualification-v2.1.json` | Planning |
| Migration support | `schemas/planning/migration-support-v2.json` | Planning |
| Readiness validation | `schemas/planning/migration-readiness-v2.2.json` | Planning and Lifecycle |

All other installed event/HTTP consumer files are enumerated by the active
registry. The two `foundation-event.json` installed names share the single
versioned `schemas/events/catalogue-foundation-recorded-v1.json` canonical
artifact. `apps/console/resources/contracts/migration-feature-policy-v1.json`
is required: the Migration Vue page imports that policy at build time.

Inventory native-input v1.3 embeds `schemas/planning/inventory-input-v1.json`
as an **active API response component**, but Planning no longer installs a
redundant v1 copy. The current Planning runtime operation mapping selects the
v2 capability input and v4 migration input.

## Current authority and qualification constraints

The Planning migration-readiness external wire `schema_version` remains 2.
The active v2.2 schema adds stricter acceptance gates while
`scripts/contracts/generate_readiness.py` reproduces the stable embedded
Planning v1.6 OpenAPI wire projection from that active profile.
Readiness is an assessment only; neither workload admission nor native provider
writes are authorized by a positive readiness result.

The v2 Lifecycle migration boundary and v2.1 worker migration-effect API
are the only active owners of their respective native operations. P07 tests
validate these current APIs and reject the old provision-stage fixture. The Inventory collection-manifest source
partitions maintain their order, including interleaved source/target/owner
attributes, and must reproduce the exact canonical bundle. Independent E3/E4
evidence and field-level transformation qualification must be commissioned
separately; a proposed E4 schema is not an authority grant or active release.

## Checks and cleanup policy

Run from the repository root:

```sh
python scripts/contracts/retirement_integrity.py
python scripts/contracts/generate_readiness.py
python scripts/contracts/generate_authority_releases.py --check
python scripts/contracts/build.py --check
python scripts/contracts/check.py
python -m unittest discover -s tests/contracts -p 'test_integrity.py' -v
```

CI additionally checks current producer responses against the exact installed
consumer, live Laravel and Python routes, JSON Schema dialects, AsyncAPI
channel/event bindings, version identities and negative denial cases. The P01
compatibility gate protects **current** canonical releases relative to the
review base and no longer replays first-publication history.

No installed JSON copy may exist merely because it is listed in the registry.
The runtime inventory independently requires a real loader, including Planning's
typed dynamic owner-operation binding, and checks byte parity for all packages.
No retired path may be reintroduced or referenced from executable source, tests,
build scripts or CI. Prospective retirements must include explicit independent
external-consumer review evidence and a recorded disposition of compatibility
commitments. `not-independently-verified` is not accepted for any **new**
retirement.

The 53 already-removed canonical versions remain a **frozen, unresolved
review backlog**, not certified external clearances. The exact roster is pinned
by `architecture/retirement-unverified-baseline.txt` and the digest in
`scripts/contracts/retirement_integrity.py`. Clearing an outstanding version
requires genuine external evidence; no repository-only scan can establish the
absence of external consumers. Previous bytes remain in Git history rather than
being copied into the working tree.

For the independent two-stage external clearance process, historically unresolved
removals and per-copy dependency evidence, see
[contract retirement and installed-copy removal](../docs/contracts/retirement-approval.md).
