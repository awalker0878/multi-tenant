# Native PlatformProfile qualification dossier

**Purpose:** implement the evidence boundary required by `QUAL-001` and `ASSUR-003`
without creating a placement controller or treating repository code as native proof.

A current qualified PlatformProfile is more specific than a platform-family capability
declaration. It binds an exact installed product/API/provider/hardware tuple to the
capabilities actually demonstrated, the assurance profiles actually tested, tested
limits, current evidence, accountable roles, and an independently controlled approval
reference.

The active machine-readable index is
[`sources/capabilities/qualification_index.json`](../../sources/capabilities/qualification_index.json).
It is intentionally empty today. That means there are **zero current native
qualification records**, which is the correct state while the actual installed tuples
remain unselected.

## Source requirements

The retained requirement catalogue states:

- `QUAL-001`: production placement requires a **current qualified PlatformProfile**
  containing the exact product/API/provider/hardware tuple, applicable features and
  licences, tested limits, evidence and approval; candidate or documentation snapshots
  are ineligible.
- `ASSUR-003`: a production profile requires approved parameters, owners, applicable
  test sets and evidence freshness limits; incomplete or expired profiles are
  ineligible for new production placement.
- `PLACE-001`: placement must satisfy all mandatory constraints using a **current
  qualified platform profile** and reject unresolved or conflicting constraints.
- `ACPT-001`: production acceptance still requires current criterion evidence,
  exclusions/risk decisions, operational-owner acceptance and a separately issued
  authorization decision.

The last item is deliberately **not** implemented by this dossier. Qualification and
production authorization remain separate decisions.

## Active record fields

A record admitted to the active index must be `CURRENT_APPROVED` and contains:

| Field | Engineering meaning |
|---|---|
| `product_tuple_id` | Stable identifier used by the capability registry; not a marketing family name. |
| `product_tuple` | Exact product version, API version, tested automation providers, hardware-profile reference and feature licences. |
| `qualified_capabilities` | Only portable capabilities actually demonstrated by this tuple. |
| `assurance_profiles` | Only assurance profiles actually included in the qualification scope. |
| `applicable_test_sets` | Test/verification sets included in the review. |
| `tested_limits` | Explicit observed bounds linked to native evidence. |
| `evidence` | Controlled evidence references, SHA-256 values, observation time, expiry time and test-set association. |
| `approval` | Accountable role, controlled decision reference and approval validity interval. |
| `owners` | Platform-engineering and security-authority roles responsible for the profile. |
| `exclusions` | Explicitly excluded capabilities, paths, limits or environments. |
| `source_refs` | Repository architecture/engineering material used to define the qualification scope. |

The checker rejects expired approval or evidence, approval that predates its required
evidence, missing tested limits, unknown capabilities, duplicate records, missing
owners, absent repository sources, and records without timezone-aware validity.

## Relationship to the capability registry

The capability registry remains the small portable summary consumed by the
platform-family pre-placement check. A future `NATIVE_QUALIFIED` capability claim must
be backed by a **current record in this index for the same exact
`product_tuple_id`**, and the claim's native evidence references must be contained in
that record's evidence set.

This means directly editing a registry capability from `NOT_QUALIFIED` to
`NATIVE_QUALIFIED` is insufficient. The qualification dossier must exist, remain
current, and cover that exact capability and tuple.

Similarly, an assurance profile cannot be advertised by the registry unless a current
qualification record for the tuple includes it.

## What a valid dossier does not grant

A valid record keeps all of these false:

- site selection
- capacity reservation
- allocation
- native apply
- production activation

The platform-family pre-placement check can use the resulting native qualification only
to say that a **family/tuple capability prerequisite** is satisfied. Site/cell
eligibility, quota, surviving capacity, location constraints, storage/key/recovery
compatibility, shared-service dependencies and operating acceptance remain separate.

The qualification approval is also not the authorization required by `ACPT-001`.

## Review command

Current repository state:

```sh
python scripts/check_platform_qualification.py
```

The expected result is a valid **empty** index:

```text
current_records: 0
qualified_capability_claims: 0
```

The disabled [example dossier](../../examples/native_platform_qualification.json.example)
is intentionally marked `EXAMPLE_NOT_APPROVED` and cannot be inserted into the active
index as-is.

[Capability registry](platform-capability-registry.md) ·
[Pre-placement family check](pre-placement-platform-eligibility.md) ·
[Qualification and authorization ADR](../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)
