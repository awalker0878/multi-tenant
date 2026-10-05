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
