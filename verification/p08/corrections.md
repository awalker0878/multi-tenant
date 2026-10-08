# P08 failures and corrections

Original observations remain immutable in the [retained index](qualification-index.json).

| Observation | Cause and correction | Verification |
| --- | --- | --- |
| Local PostgreSQL setup unavailable | This execution container cannot create the unprivileged database account (`chown` returns EINVAL). The test/runtime restrictions were retained; local skips were not promoted to passes. | Hosted PostgreSQL 16 campaigns ran all service/worker database checks without skips. |
| Data-path run `37591411211` at `8d536e4` failed | `test_migration_runtime.grant()` returned untyped `json.loads` data from a typed function. Strict mypy correctly rejected it. Commit `712ea5d` adds the explicit fixture type. The original 09.log/report remain unchanged. | Run `37592344373` passed; retained final run `37592736006` also passes all 20 commands. The original run remains FAILED even though its runtime tests passed. |
| Completion handoff review | The archive completion receipt did not bind the aggregate disk receipt digest. Commit `712ea5d` binds and validates that digest and rejects disk events after completion. | Final real PostgreSQL tests reject wrong completion digests and late disks; conversion handoff tests exercise missing custody, wrong disk sets/bytes/digests and uncertain conversion. |
| Threaded process-launch review | A `preexec_fn` resource hook could deadlock after a multithreaded fork. Commit `a72d0e8` moves limits into a fresh isolated interpreter before the pinned sandbox is executed. | Real threaded subprocess file/output/deadline tests pass locally and hosted. Their synthetic launcher is explicitly not a QEMU/bubblewrap qualification. |

The new launcher test first selected the large Python binary as its synthetic
sandbox artifact, exceeding the production sandbox-file size bound before launch.
The fixture was corrected to use an explicit small synthetic artifact and to
assert the precise expected failure reasons; no production bound was relaxed.
The file-limit probe explicitly flushes the file so buffering cannot hide its
result. These local test-authoring failures are not native campaign failures.

Earlier component authoring also corrected a missing pytest fixture import and
explicit dictionary types before publication. No production fallback, quality
rule, authority boundary or acceptance criterion was weakened.

The [regression receipt](regressions/failure-receipt.json) retains the original
P06 Firefox archive from `37592344371`: namespace bootstrap exited with signal 11
and an empty command log before the Temporal journey. The root cause is not
established. Its 1,078 source bindings and 41 command logs match; the later
`37592736181` run passes all P06 jobs and all three browsers with unchanged P06
campaign scripts. No timeout, test requirement or retry policy was relaxed.
The original failure remains FAIL. The earlier P06 core failure at `8d536e4`
was the same strict mypy fixture defect recorded above.

[Workflow observations](source-regression-observation.json) retain all 14 passing
control-checkpoint runs and all eight passing final-source runs, including the
intermediate failed workflows at their original commits. These statuses establish
software regression outcomes only.
