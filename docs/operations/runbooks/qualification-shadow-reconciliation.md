# Qualification shadow reconciliation — read-only engineering gate

This runbook applies to [PR #64](https://github.com/awalker0878/multi-tenant/pull/64)
and `scripts/assurance/shadow_compare.py`. Shadow comparison **does not grant**
native E3 support, accepting E4 authority or a rollout. The independent Assurance
reviewer and receiving service owner retain every decision.

## Inputs and custody

Capture two independently attributable, read-only snapshots from the approved
qualification inventory. Provide a baseline and a candidate file; do **not**
allow either manifest to publish qualification or change an adapter registry.
Each JSON file has the exact keys `schema_version` (1), `source_revision`
(a 40-character lowercase commit hash) and `records` (0–500 rows).

Each record has `scope_sha256`, `authority_epoch`, `state` (unknown,
qualified, suspended, revoked), `decision_sha256`, `evidence_level` (null,
E2, E3, E4), `definition_sha256`, `adapter_sha256`, `runtime_sha256`,
`native_tuple_sha256`, `platform`, `method` and `expires_at`.
Hash values are lower-case SHA-256; null hashes describe unknown provenance,
not an accepted positive result. A qualified state must at least have
decision/definition hashes and a positive epoch. **This is a shape check, not a
cryptographic reviewer verification**. Manifests must be created under proper
independent source control; no user-supplied document confers native evidence.

## Offline comparison

```bash
python scripts/assurance/shadow_compare.py \
  --baseline /approved/evidence/baseline.json \
  --candidate /approved/evidence/candidate.json \
  --output /approved/evidence/new-shadow-report.json
python -m unittest discover -s scripts/assurance -p 'test_*.py' -v
```

The output is always a new file. It includes both source revisions, the hashes
of the original input files, each changed scope and its drift reasons. It
does not include native credentials, raw source evidence, signed reviewer
decisions, or any operation capable of writing authority.

- Exit **0** means no differences in these snapshots, **not** qualification.
- Exit **1** means at least one scope changed; human independent reconciliation
  is mandatory for state, epoch, method, definition, adapter, runtime, installed
  tuple or expiry drift.
- Exit **2** means invalid/unreadable manifest or unsafe output path; no positive
  conclusion is possible.

## Promotion gate

A difference report must be mapped to reviewed evidence, required negative
cases, scope and source commit, provider custody, no regression in future
native admission, workflow compatibility and actual receiving-owner review.
Treat old positive states, stale/unknown scope, expired signatures and
unavailable owner reads as holds. No automatic acceptance, migration, SQL
authority update or catalog rewrite follows comparison. See
[`next_work.md`](../../../next_work.md) CT-N12 and A01–A16 for the
authoritative unfinished work.
