# Native API component qualification

The [qualification index](qualification-index.json) retains original hosted
archives, report snapshots, source/log/artifact digest verification and all earlier
failures. Run `python scripts/p07/verify_retained_native_api.py` from the repository
root to reproduce verification against the original Git commits. The archive
manifest binds GitHub run/artifact identities and original archive SHA-256 values.

The native API baseline is implemented at `eaf060b5`; fixture digest rebinding and
durable journal tests are at `06a329d0`. Source `4ee67fdd` removes generated Python
package metadata from version control and repeats affected qualification.

## Measured scope

- The P07 component campaign passes 276 Lifecycle and 139 worker tests with real
  PostgreSQL and no skips. Fourteen commands cover contracts, formatting, lint,
  types, tests and package builds. Synthetic TLS peers exercise native OpenStack
  creates/readback and VMware export/Glance import; no native platform is tested.
- The native Temporal campaign passes 43 checks and replays six histories through
  the actual Temporal runtime. The original histories remain beside each report.
  Current owners and stage effects are synthetic.
- Commissioning preparation passes 93 tests. Its incomplete installation packet
  correctly exits 2 under `--require-complete`; a passing denial is not commissioning.
- P05 and P06 browser campaigns exercise the actual Console and owned services in
  Chromium, Firefox and WebKit: 73 P05 checks and 148 P06 checks per browser at
  `4ee67fdd`, with every recorded source binding matching Git. Their fault commands include process
  exit 75 and denied dependency access; outcome assertions and logs are retained.
- P06's core job skips ten worker persistence cases because it does not configure
  that worker's native database fixture. All ten run without skips in the separate
  mandatory P07 component job. Do not describe the P06 core job as having no skips.

## Original failures and corrections

1. The first P05/P06 browser runs fail on `native_operation_scope_changed`: the
   fixture changes workload identities without rebinding the native ownership and
   operation digests. `06a329d0` recomputes both canonical bindings. All original
   failed browser archives remain failed in the index.
2. The initial contract-freeze job rejects the intentional replacement of nine
   published Terraform-era contracts/fixtures. Its original failed archive is
   retained. No freeze policy or check is relaxed, and no compatibility contract is
   introduced. Subsequent source revisions validate the native-only baseline.
3. Six earlier P06 browser reports contain a source hash mismatch for the tracked,
   generated `services/lifecycle/src/product_lifecycle.egg-info/PKG-INFO` file.
   Installation regenerated the metadata before recording the campaign bindings.
   The index explicitly records the mismatch and both hashes; it does not claim
   those bindings match Git. `4ee67fdd` removes tracked generated metadata and
   ignores future generated copies. Verification requires every current-source
   binding to match Git.

## Acceptance limits

This is E2 engineering evidence. Actual current-owner/caller-trust composition,
native request fencing and selected guest, reservation, service, traffic and
retirement integrations remain unfinished. Q05/Q06 native campaigns and G07
receiving have not occurred. P07 remains incomplete.

The export/import component is partial P08 M3/M4/M6 work; it does not implement
snapshot/clone capture, OVF generation, disk conversion, guest transformation or
application/file-delta cutover. The [P08 design](../../../docs/implementation/p08-native-migration.md)
defines that work separately.
