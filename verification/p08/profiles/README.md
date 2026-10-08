# P08 profile and review qualification

The [verified index](qualification-index.json) binds original hosted ZIPs to exact
Git source bytes, command logs, JUnit counts and retained browser artifacts.
Run `python scripts/p08/verify_profiles_retained.py` with those Git objects present.
Earlier [P08 component evidence](../qualification-index.json) remains unchanged.

The final component run at `497c660670130654f62a73987755d69c6b444641` passes all 34
commands and 779 tests with no skips: Inventory 90, Planning 119, Lifecycle 304,
Lifecycle-worker 204 and Inventory-worker 62. It verifies 667 source bindings.

| Surface | Measured behavior | Boundary |
| --- | --- | --- |
| Collection | Eight source and seven target GET permits; current worker/lease/policy/authority, source membership, pacing, permit replay and mid-read revocation | Real PostgreSQL and synthetic native responses; actual enrollment/installed tuple required |
| Profiles and review | Immutable complete-generation profiles; cross-tenant denial; complete dataset coverage; owner-only inputs; exact revision/digest confirmation; stale/revoked current reads | Real PostgreSQL, synthetic authority peers |
| Planning preparation | Authenticated actor and exact Inventory owner read; native capacity/dataset derivation; unsupported/foreign/duplicate/missing mappings denied | Binding preparation only; complete native plan composition remains required |
| Lifecycle admission | Exact current review, profile identities, owner-input digest, method/objectives, every disk/dataset/capacity/format | Real PostgreSQL with synthetic current owners; native stage composition remains required |
| Console controller | Six PHP feature cases and 37 assertions for scoped review, confirmation and failed/uncertain responses | Isolated Laravel service mocks; hosted Console package tests cover the same source |
| Browser | Actual Vue/Inertia page; explicit method, all-disk mapping, uncertain unchanged retry, dirty/stale confirmation denial, access revocation, safe text and narrow viewport | Isolated synthetic HTTP fixture; original results recorded separately, no real operator/assistive review |
| Contracts | Inventory v1.2, Planning migration v1 and exact owner schema; eleven injected native/authority fields denied | Existing canonical contracts restored byte-for-byte and independently checked against pre-increment source |

## Original failures and corrections

- `7deab35` incorrectly extended frozen Inventory v1.1 contract bytes. The strict
  contract run `37614814472` failed. `b975c8f` restores those exact original bytes
  and adds v1.2. The strict adjacent-commit check `37615241995` also records this
  restoration as a change and remains FAIL. The original-baseline comparison
  against `891753c` verifies every prior contract unchanged; the subsequent strict
  run `37616461458` passes all 24 commands. No compatibility rule was relaxed.
- The initial browser run `37616461456` fails before rendering because the isolated
  fixture used an old DOM page-discovery convention. `104527f` supplies the initial
  page explicitly to the installed Inertia API. The real Console's Laravel/Inertia
  bootstrap was unaffected. The original trace/screenshot/logs remain FAILED.
  Run `37616927824` at `104527f` then passes all five browser quality commands and
  the full journey with no skipped/flaky tests or browser errors. Its full-page
  screenshot was visually inspected; controls and dataset coverage render correctly.
- The first browser report included Playwright's `.last-run.json` hash, but the
  hosted uploader excludes hidden files. The index explicitly records this one
  unavailable artifact; it does not claim its bytes were verified. The qualifier
  now hashes only retained non-hidden artifacts. All supplied artifact bytes are
  independently verified; no missing diagnostic is reconstructed as original.
  Final run `37617605574` at `497c660` passes component and browser qualification
  with every reported artifact present and verified.
- P03 WebKit and P04 Firefox runs at `a225348` fail with `broker_not_ready`.
  The P04 original broker log specifically records unreadable Erlang cookie
  permissions (`eacces`); P03 did not retain a broker crash log, so its specific
  cause remains unestablished. `497c660` runs both fixtures' early health probes
  and ready checks as `rabbitmq` rather than root and adds P03 crash diagnostics.
  This addresses the root probe's ability to create a cookie that the broker
  cannot read. The pinned image's [official packaging](https://github.com/docker-library/rabbitmq/blob/master/Dockerfile-ubuntu.template)
  provides `gosu` for that identity. No readiness check, timing bound or retry
  policy was weakened; the original failures remain FAIL.
  Corrected P03 run `37617605608` and P04 run `37617605566` pass all three browser
  engines and the service integrity suites.
- Intermediate P06 Chromium run `37616927845` fails in real Temporal namespace
  bootstrap, before the application/browser journey. Its original archive remains
  FAIL; no native or application failure is inferred from an empty command log.
  Final-source run `37617605699` passes every P06 job and all three browsers.
  The Temporal bootstrap implementation and qualification bounds were unchanged.
- Local browser execution cannot start because Chromium is absent. Local database
  skips and missing-browser failures are not passing qualification. Hosted runs
  supply the required actual browser and unprivileged PostgreSQL runtime.

No installed converter rootfs, copied guest, native VM/image, application delta,
service/traffic/fencing adapter or post-write data recovery is qualified here.
Q07, actual G07/G08 receiving and P08 completion remain open.
