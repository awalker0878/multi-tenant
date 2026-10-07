# P10 operating qualification tools

Run `python scripts/p10/qualify.py --output /absolute/output` from a clean checkout
with `P05_POSTGRES_BIN` pointing to PostgreSQL 16 binaries. The pinned hosted
workflow supplies that environment. The runner freezes source, retains originals,
runs the full Planning/Lifecycle/worker suites without permitted skips, validates
P07/P08 compiler composition, exercises local TLS alert receipt and artifact
controls, and records the synthetic workload and real database restore.

A passing engineering report is E2. It does not establish native throughput,
full control-plane RPO/RTO, actual on-call receipt, restricted installation or G10.

`python scripts/p10/dossier.py --output /absolute/output` freezes the exact clean
candidate and reconciles `release/p10-inputs.json`. Exit 2 means the packet is
held; exit 1 means an invalid record or read failure. Even a complete packet
requires independent authentication and review and never authorizes release.
There is no switch to omit required cases or promote E2 to E3/E4.

The actual input record deliberately contains nulls. Supply content-addressed
references to the selected qualified tuples, G07/G08/G09 decisions, approved
workload/SLO model, exact image/lock/SBOM/provenance/signature set, versioned security
findings and custody review, and actual operations receipts. Each Q09/Q10 case
binds the frozen candidate and complete source map, measured scope, result,
failed/skipped counts, environment and evidence level. Each package needs its
independent receiving decision. File hashes prove integrity; reviewers must
verify the origin and truth of every submitted observation separately.

Reusable evaluators:

- `metrics.summarize` includes every supplied attempt and every selected tenant.
  It records nearest-rank latency percentiles, errors, throughput and Jain fairness.
  Without approved targets it returns `NOT_EVALUATED` for SLOs. Its input boundary
  and measurement window must be retained; these cannot be changed to hide failures.
- `recovery.assess_restore` requires all eight coordinated dependency groups,
  matching recovery points, read-only isolation, changed independent epoch,
  quiescent known native outcomes and the mixed-version/replay/backfill/key/drain
  observations. Packet completeness cannot re-enable a writer.
- `mirror.verify_closure` verifies bounded artifact paths, lengths and digests for
  each expected component's image, lock, SBOM, provenance, signature and trust root
  without extraction or downloads. It does not validate signer trust or prove a
  restricted runtime install; use the existing P01 bundle admission and the real
  Q09.09 campaign for those observations.

The load exercise uses twelve synthetic tenants, 48 operations, eight dispatchers
and a shared four-slot endpoint. The separately reported operation latency spans
boundary authorization through independent reconciliation; it excludes queue wait
and claim latency. Total throughput includes setup after enqueuing, dispatch,
saturation checks and revocation probes. These measurements are a reproducible
small integration workload, not the estate capacity model.

The restore exercise uses actual `pg_dump`/`pg_restore` of a disposable Lifecycle
database while its synthetic custody owner advances independently. The restored
old grant must be denied. Other control-plane stores, real old workers, provider
requests and independent custody require the full Q09 deployment campaign.
