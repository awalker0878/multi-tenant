# Profile model

A profile is a named, reviewed, ranked option in exactly one family. Catalogs live
at `profiles/<family>/catalog.json`; the directory is the only index, so there is
no second profile list that can drift.

Loader: `provisioner/profiles/loader.py`
Resolver: `provisioner/profiles/resolver.py`
Validation: `provisioner/profiles/validation.py`

## Families

`environment`, `security`, `assurance`, `availability`, `recovery`, `compute`,
`storage`, `network`, `service`, `placement`.

`placement` holds the region profiles (`east`, `west`, `public`).

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `IMPLEMENTED_INTERNAL_IPV4_OZ_RZ` | reviewed and usable by a request in this repository |
| `DEFERRED_NOT_IMPLEMENTED` | declared so the refusal is explicit; selecting it is refused |

A deferred profile is never silently downgraded to a neighbouring profile. The
refusal is `UNSUPPORTED_PROFILE` with the deferred name in the diagnostic.

## Resolution

Resolution is a pure function of the request and the catalogs:

1. Each family name is looked up. A missing name is `UNSUPPORTED_PROFILE`.
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
`service_class`, `services`, `storage`, `trust`, `zones`.

## Rank

Every profile carries a rank inside its family. Rank is used for minimums
(`environment: production` needs availability rank ≥ `high`) and for deterministic
tie-breaking. Rank is never used to substitute one profile for another.

## Adding a profile

Add the entry to the catalog with an explicit status, then add a regression to
`tests/provisioning/test_profiles_policy.py`. A catalog entry without a regression
is not reviewed. Removing or renaming a profile is a breaking change to the
request contract and needs a note in the retired-interfaces register.