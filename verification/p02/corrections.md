# P02 qualification corrections

The original observations remain unchanged. These are development results, not
receiving gate decisions.

| Source/run | Observation | Correction |
| --- | --- | --- |
| `d45d0aa83582c5376335c10d033b60d7e549d979`, [contract run 37353917453](https://github.com/awalker0878/multi-tenant/actions/runs/37353917453) | Existing local-identity schema bytes changed; the exact-version freeze rejected them. | `6fd44860f61d66bf858c92b8099f29a97479758b` restores the original published schema and its controller projection. The new federation API remains the source for current configuration state. No freeze rule or exclusion changed. |
| Same source, [P02 run 37353917458](https://github.com/awalker0878/multi-tenant/actions/runs/37353917458) | 55 PostgreSQL feature cases pass (952 assertions). Browser bootstrap, HTTPS provider configuration/handover and tenant creation work, but the reader test uses the preceding account URL because it samples before Inertia navigation finishes. The campaign is FAIL. | The test waits for the selected tenant heading before capturing its URL; authority assertions remain intact. |

The [failed P02 report](identity/run-37353917458/report.json),
[failed contract report](contracts/run-37353917453/report.json) and
[corrected original-baseline compatibility comparison](contracts/restored-compatibility.json)
are retained. The corrected comparison freezes the original accepted artifact
bytes at `f3612f6d5669ec47f13020a7f1f1f1d64e333e5d` and accepts only the three new
contract files. Its result does not relabel either failure. The [next contract run 37354292360](contracts/run-37354292360/report.json)
conservatively compares with the previous push and also sees the restoration as a byte change
relative to the rejected edit. The [unchanged-artifact regression at b1064b7](contracts/run-37354711828/report.json) passes the original unmodified check, along with generated-client and HTTP conformance replay. No failed run is treated as a passing gate.


## Governance delivery qualification

The initial `ab8570145870ed6d2c9d5c0a65a471f90e3315ab` runs are retained:
[identity/relay run 37358072207](identity/run-37358072207/report.json) and
[broker startup run 37358072439](events/run-37358072439/report.json).
The first exposed a timestamp precision mismatch: PostgreSQL's fractional
`available_at` default was compared with a Laravel seconds-only binding, making
new events appear temporarily unavailable. The second called the broker CLI
before its Erlang node finished starting. Neither is a passing campaign.

`4afcee1d504b8dfb0725d3306f8c2c55eb1f6dce` retains microsecond precision in the
relay eligibility comparison and waits for actual broker health/port readiness.
No authorization rule, time limit or assertion was relaxed. Corrected campaigns
37358891052 (identity/browser) and 37358890871 (PostgreSQL/TLS broker) pass;
their measured source remains distinct from subsequent delegation work.

## Evidence transfer fidelity

One Chromium dependency-install log contains carriage-return progress updates.
The initial evidence transfer normalized those bytes; `f8f4e8972170f521cfd840f23528af7ea314bb17`
restores the original downloaded bytes and recorded digest. The reports and test
outcomes are unchanged. Catalogue/Console package artifacts use the existing
`verification/p01/packages/run-<id>/<component>/` layout because they originate
from the P01 package workflow. Its architecture check validates both report/source
bindings; no source-registration exception was added for P02.

## Console notification image platform requirement

At `88e44414e4add9706435e49d869090cc1b5f81c5`, Compose run `37371171458`
fails during the Console image's Composer platform validation: locked AMQP library
3.7.5 requires `ext-sockets`, which the Console image did not compile. The
[original failure](../p01/local/run-37371171458-notification-image-failure/retrieval.json)
retains all downloaded reports/logs, 86 verified command logs and 388 unique source
bindings. Installation did not begin. The same image failure on the subsequent
`283e6f4` campaign remains a failed workflow, not a passing runtime observation.

`b13996d13db9b54736667a04be23c53f74269424` compiles the sockets extension
using existing pinned build inputs and explicitly declares it in Console's root
manifest/lock. No dependency is updated and no platform requirement is ignored.
The [local platform checks](console-notifications-platform/report.json) pass.
The corrected [Compose run `37371858448`](../p01/local/run-37371858448/retrieval.json)
passes 249 checks; all seven image build/process reports pass. The complete original
archive, 612 command-log hashes and 451 unique source bindings were verified.
Image-security admission, independent package replay, Kubernetes and browser-engine
results remain separately scoped; neither old failed workflow is relabelled.

## Browser quota-save synchronization

WebKit run `37371858388` at `b13996d` passed the bootstrap journey but failed
the federation journey with a quota request network error. The test navigated
before the submitted request had necessarily finished. The
[original report](identity/run-37371858388/webkit/report.json) and downloaded
archive retain that failure. Concurrent commit `9716803` waits for the actual
redirected owner response, checks the returned quota and waits for form
processing before navigation. No assertion, network-error check or browser is
excluded; hosted correction results remain required. See the
[synchronization record](../../docs/implementation/p02-browser-synchronization.md).

## Pending build displacement

GitHub's default concurrency queue preserves only one pending run even with
`cancel-in-progress: false`. Later documentation pushes repeatedly replaced
pending changed-source package/image runs. Image run `37371858446` was cancelled
before creating any jobs; its failed-jobs retry was rejected with HTTP 403
(`This workflow run cannot be retried`). This is distinct from a failed product
test or an approval rejection.

Package, image, Compose and Kubernetes workflows now opt into GitHub's documented
[`queue: max` FIFO behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency),
which retains up to 100 pending runs while preserving one active run per group.
The workflow-input change conservatively selects all candidates through the
existing selector. Check names, required assertions, platform/security checks,
failure aggregation and permissions stay in force. The new full campaign needs
its own results; this configuration change is not a passing image admission.


## Installation relay migration replay and isolated package fixtures

At `a2c522458c9f61966f794096c435c95464f6b427`, identity run `37376902084`
fails in all three engines because its fixture replays only migration 001 after
the complete migration set, removing later identity-outbox UPDATE grants. The
[original Chromium report](identity/run-37376902084/chromium/report.json) and
archive preserve the failure. `3a5ef6e` replays every ordered migration, retaining
the same runtime least-privilege grants and all delivery assertions.

The same source's package run `37376902098` exposes Console and Governance
tests that read repository-root schema paths outside their independently packaged
applications. The original [Console receipt](corrections/run-37376902098/console/retrieval.json)
and [Governance receipt](corrections/run-37376902098/governance/retrieval.json)
retain the failures. The correction checks the packaged schema against its fixed
published digest locally; the integration campaign still compares exact published
repository bytes. No application package reaches into a sibling package and no
contract-freeze exclusion changes.

Corrected [run 37377875499](recovery-three-engine-index.json) passes all three
98-check identity jobs. [Run 37378369526](approval-history-three-engine-index.json)
adds nonempty approval-history recovery and passes 100 checks in each engine.
The nine isolated package jobs at `fe88107` also pass; their exact workflow
identity is in [the hosted receipt](completion-hosted-runs.json).

## Local command-log filename collision

The unregistered [initial recovery E1 report](recovery/local-20261005/report.json)
reused `console-types` and `console-boundaries` filenames for PHP and frontend
commands. Four original PHP stream hashes therefore do not match the overwritten
files. Its stored PASS field is not accepted as complete evidence and is left
unchanged. The [correction receipt](recovery/local-evidence-correction.json)
records each mismatch without inventing the lost streams.

The [full rerun](recovery/local-final-20261005/report.json) at `ec4c773` uses
distinct `console-frontend-*` filenames. All twelve commands pass; the separate
[verification receipt](recovery/local-final-20261005/verification.json) checks
all 24 streams and 294 exact-commit source bindings. EV-P02-017 registers only
this corrected evidence. Hosted campaign artifacts did not have this collision.

## Support concurrency observer — 2026-10-05

Source `cac287efce9ab8e72db0b2795feb8217a56aa714`, identity run
`37386102114`, passed 176 PostgreSQL cases but failed the new concurrent-revocation
observer in all three engine jobs before browser execution. The observer retained
its own transaction's initial `pg_stat_activity` snapshot and never observed the
later waiting process. The original reports, logs and archives are retained under
`verification/p02/support/run-37386102114/`; these runs are not passing evidence.

[PostgreSQL 18 documents the per-transaction activity snapshot and explicit refresh](https://www.postgresql.org/docs/18/monitoring-stats.html).
Correction `ad53968f4f3f4c9c1bc031a17f909be4ff6dabf2` calls
`pg_stat_clear_snapshot()` for each observation while retaining the real row lock,
and requires the waiter to be blocked specifically by this test's backend PID.
The wait assertion, denied-result assertion, zero-admission check and terminal
invalidation check remain mandatory. No application or contract behavior changed.
Corrected-source run `37386462647` passes all three engines: 116 checks, 177
Governance PostgreSQL cases (4,325 assertions), 66 Console PostgreSQL/TLS cases
(248 assertions), and both compiled browser journeys per engine. The corrected
TLS event run `37386462663` passes 74 cases (1,358 assertions). Original and
corrected archives are indexed by `verification/p02/support/qualification-index.json`.

The separate real TLS event campaign at the original source passed, including
publisher-crash replay and Console/support-audit queue separation. Its original
archive is retained under `verification/p02/support/run-37386101997/events/` and
remains separate from the failed identity campaign.


## Independent recovery ceremony observations

Source `f5dbba62bc017632893d6220cbba3f9b3dac5e03`, identity run
`37393173334`, failed all three campaigns at the new recovered-identity check.
Real owner reconciliation, separate encrypted-key signatures, full-schema restore,
independent custody release and fresh OIDC callback had completed. The observer
incorrectly selected `CurrentIdentity` from the frozen local-bootstrap schema,
which requires the local administrator and does not describe a federated identity.
All three original reports, logs and ZIP archives are retained under
`recovery-custody/run-37393173334/`.

Correction `153b771f0b85135eae45f7d5c929fbbb5f4aae74` requires the **complete exact**
recovered federated actor, identity kind, password-change state and permissions.
No published contract or existing local assertion changed. All three corrected
campaign jobs passed. Final hardening `7ec7a60623f60c84ba3356978f0ff51b03e9ca7e`
also rejects assigning any old credential to another workload, in addition to
rejecting shared current credentials. Its local and hosted results are indexed
in [the recovery qualification](recovery-custody/qualification-index.json).

Earlier foundation source `ad3897d`, Kubernetes run `37392747755`, failed because
the second Console shared-state helper returned zero bytes with exit zero; strict
JSON parsing rejected the observation. The [original archive and verified receipt](recovery-custody/run-37392747755/kubernetes/retrieval.json)
retain all 874 members, 826 verified command-log bindings and 471 exact source
bindings. The initial shared-state write had passed. The unchanged observer later
passed the full Kubernetes campaign at `ec60406` (run `37393081051`). This does not
relabel the earlier failure or waive the final-source Kubernetes regression.
