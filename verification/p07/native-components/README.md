# P07 native adapter component evidence

This is an E2 software component increment, not native P07 completion. The
[verified index](qualification-index.json) binds original reports and archive
bytes to exact revisions. Final worker source is
`dd31bed12de3133b30f0a06072ada37abd9f4961`; its 112 tests run without skips and all
ten quality/build/Terraform commands pass. The final report is
[retained here](final/report.json).

| Boundary | Observed software checks | Limit |
| --- | --- | --- |
| Saved plan | Actual protected file hashes, exhaustive bundle inventory, exact subprocess arguments, workspace/state serial comparisons, unknown/changed fields, ownership and quarantined creates | Synthetic plan command peer; real Terraform separately validates/schema-tests the module. No actual backend or native apply |
| Terraform module | Pinned Terraform 1.13.5 executable and provider 3.4.0 lock, format/validate and mocked plan for two workloads, three NICs, IPv4/IPv6 and retained boot disks | Development schema candidates, not deployment selection or native support |
| Durable attempt | Real PostgreSQL TLS, 16 competing deliveries, one committed claim, changed-binding and shared-lineage denials, runtime privilege rejection and reconnect persistence | No independent restored-journal reconciliation or hold release |
| Authority and process | Injected current-authority port denies preflight/prelaunch/during-run effects; real subprocess interruption and bounded private output | No product native grant redemption or provider-side request fencing |
| Native HTTP | Real trusted TLS to a synthetic peer, literal address/hostname checks, fixed service paths/versions, scope-bound token reuse, redirect/path/rotation/size denials | No installed OpenStack platform qualified |
| Independent readback | Exact state IDs, Keystone scope, object ownership, disk/NIC mappings, placement/image/config-drive, security groups/addresses/quarantine; missing/changed data stays held | Configured identity separation does not establish actual permissions; no application readiness or absence certificate |
| Strict data | Duplicate/nonfinite JSON, booleans substituted for numbers and timezone-free expiry cannot satisfy evidence comparisons | Software parsing assertions only |
| Packaging and integration | Installed read-only command is registered in the worker image manifest; native journal migrations are isolated from simulation migrations | Native dispatch remains disabled; image admission is a development result |

The [runbook](../../../docs/operations/runbooks/openstack-native-adapters.md) defines
the exact commands and supported fields. The [remaining packet](../../../docs/implementation/p07-completion-review.md)
retains product native authority/fencing, guest and enterprise service integration,
activation, recovery/retirement and Q05/Q06 obligations. Successful infrastructure
readback grants no retry, hold release, application readiness or activation.

At the final source, Chromium, Firefox and WebKit each pass all 148 P06 checks and
three browser journeys. Each report's 1,052 source hashes, 61 command logs and 81
artifact hashes match. P06 core separately passes 184 Lifecycle, 49 execution and
104 worker cases; its eight optional native journal cases are skipped there and
all run without skips in the P07 worker job. The
[workflow receipt](regression-completion.json) records 17 passing workflows at
their own revisions, including worker development image admission and the wider
Compose/Kubernetes deployment regressions.

## Original observations and corrections

- `d561a5f` passed 102 worker tests; `f63db0e` passed 107. Their original reports,
  command logs and ZIP bytes remain under `initial/` and `integration/`. Final
  `dd31bed` adds five strict-type/expiry cases and passes 112. Each has its own
  source bindings; earlier observations are not rewritten as final-source tests.
- Image jobs `112596303043` and `112597312911` failed the existing owned-entrypoint
  check because the new read-only command was missing from the build manifest.
  Their decoded original logs remain in `failures/`. `f63db0e` registers the command;
  subsequent image admission succeeds without relaxing the check.
- Five P06 live campaigns in runs `37560443078`/`37560765849` failed because the
  simulator's root migration glob attempted the native schema in its own database.
  `f63db0e` moves the native migration to `migrations/native/`, preserving separate
  database ownership and runtime privileges. The original archives and reports
  remain failed. The corrected P06 campaigns run separately.
- The first WebKit campaign in run `37560443078` stopped earlier: RabbitMQ could
  not read its ephemeral Erlang cookie (`eacces`). Its original archive retains
  the broker diagnostics. That observation is distinct from the migration defect;
  later independent campaigns passed. No native or product result is inferred
  from the failed startup.
- Initial local PostgreSQL fixture setup could not change ownership to UID 65534
  in this container (`EINVAL`). The hosted worker campaign runs those eight real
  persistence tests without skips; no local database pass is claimed.
- Initial local checks also found an ambiguous double-slash HTTP path and an
  oversized pytest-generated case label. Both were corrected before `d561a5f`.
  Subsequent inspection added readback for every claimed optional field and excluded
  ambient Terraform CLI configuration overrides in `9077e55`. Strict type and
  timezone comparisons are corrected in `dd31bed`.

Archive files use `.zip.b64` to preserve their exact binary bytes through this
repository publication path. Decode with standard Base64 and compare the ZIP
SHA-256 in the index before extracting. Original failures are never counted as
passes. The register retains P07 `IN_PROGRESS` and G07 `NOT_REVIEWED`.
