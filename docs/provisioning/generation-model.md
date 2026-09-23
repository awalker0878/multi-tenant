# WSD identity and generation model

A plan answers two different questions that must never be confused: *what* is being
changed, and *which* change it is. The first is the **WSD identity**; the second is
the **generation**. Both are derived from reviewed state, both are bound into every
artifact the pipeline produces, and neither is an authorization.

Model: `provisioner/domain/generation.py`
Formats: `hosting-wsd-identity/1`, `hosting-wsd-generation/1`,
`hosting-wsd-generation-ledger/1`
Ledger authority: `EXTERNAL_LEDGER_ONLY`

## Identity

The identity is the five identifiers that name one WSD, exactly as the existing
`hosting-delivery/1` scope names them:

| Component | Meaning |
| --- | --- |
| `tenant_key` | the tenant |
| `wsd_key` | the WSD name |
| `environment_key` | the environment identity, `{site_key}-{lifecycle}` |
| `site_key` | the site |
| `platform` | the platform family the environment resolves to |

The canonical key is
`{tenant_key}/{wsd_key}@{environment_key}/{site_key}/{platform}`, and the identity
digest is the canonical digest of those five components. Every component must match
the scoped-identifier grammar `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$` — the same rule
`tools/delivery_run.validate` already enforces through `tools.readback_core.ID`. The
identity is **derived** from the resolved desired state rather than stored beside it,
because the desired state already carries all five components and a second stored
copy could only drift.

## Generation

A generation is a positive integer that only moves forward for one identity. The
first generation of an identity is `1`. The generation is claimed by the caller
(`--generation`), recorded in the desired state, and then bound into the plan
identity, the delivery plan, every owner operation, the observations, the
conformance report and the recorded evidence.

A generation is a change counter, not a secret and not a lease. Nothing in this
repository increments one: a local counter is not authority, and the module that
defines the semantics cannot read a filesystem, a database or a clock.

## Ledger and claim semantics

The authoritative record of which generation is current belongs to the owner that
holds it. The repository defines the interface (`GenerationLedger`: `current()` and
`compare_and_set()`) and the semantics; `InMemoryLedger` exists so the semantics can
be exercised deterministically in tests, and every result it produces says
`IN_MEMORY_NOT_AUTHORITATIVE`.

`claim()` applies one rule set:

| Situation | Outcome |
| --- | --- |
| No record held, generation `1` | `CLAIMED` |
| No record held, generation above `1` | refused `GENERATION_CONFLICT` — the first generation is `1` |
| Same generation, same desired-state and plan digest | `REPLAYED` — no duplicate external operation |
| Same generation, changed desired state or plan | refused `GENERATION_CONFLICT` — changed desired state requires a new generation |
| Lower generation than the held one | refused `STALE_GENERATION` |
| Higher generation, held record `CLOSED` | `CLAIMED`, and the held record is reported as superseded |
| Higher generation, held record `OPEN` | refused `GENERATION_CONFLICT` unless reconciliation states it decided the unfinished operation |
| A ledger that returns a record for another identity | refused `GENERATION_IDENTITY_MISMATCH` |

Two claimants that both read the same held record cannot both become current: the
commit is a compare-and-set against the record they read, so the second one is
refused `GENERATION_CONFLICT` rather than silently overwriting the first.

## Operation identity

The operation identity for one generation of one WSD is derived, never chosen:

```
{wsd_key}-g{generation}-{plan_digest[:12]}
```

The same reviewed plan always produces the same operation identity, so a resumed run
recognises its own operation instead of creating a second one. A changed plan or a
later generation produces a different operation identity, which is what makes a
stale operation distinguishable from a current one. The delivery plan names each
owner operation `{operation_id}-{step}`, and the separator is `-` rather than `:`
because `:` is outside the scoped-identifier grammar.

## What the generation is bound into

| Artifact | Binding |
| --- | --- |
| `DesiredState` | `generation` field, and `identity` derived from it |
| `Plan` | `generation`, `identity`, `operation_id`; the generation is the first term of the [reviewed-plan manifest](plan-manifest-model.md), whose digest is the plan identity |
| Delivery plan | `generation`, `identity`, `operation_id`, `plan_digest` on the plan and on every owner operation |
| Observations | each observation carries the generation it was read at |
| Conformance report | `generation`, `identity`, `operation_id` |
| Evidence | every record carries `generation`, plus a dedicated `generation` record |
| CLI | `status`, `verify` and `apply` report the generation, identity and operation identity |

Because the generation is a term of the reviewed-plan manifest, claiming a later
generation changes the plan identity, the operation identity and the conformance
report without changing the request.

## Refusals

Generation refusals use the `generation` layer of `provisioner/domain/errors.py`:
`GENERATION_CONFLICT`, `GENERATION_IDENTITY_MISMATCH` and `STALE_GENERATION`. A
generation is only ever a positive integer: `0`, `-1`, `True`, `'1'` and `None` are
all refused, and `tools/delivery_run.validate` refuses the same values, so the
portable model and the delivery runner cannot disagree about what a generation is.

## What this model is not

A recorded generation is a reviewed change counter, not an approval. `claim()`
authorizes nothing, contacts no native system (`native_contact` is always `false`),
and the repository never holds the authoritative record. External execution
authority and production approval remain required, and an observation from an earlier
generation is reported stale — never accepted as current conformance.