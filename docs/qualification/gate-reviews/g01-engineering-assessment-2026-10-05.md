# G01 engineering assessment — 2026-10-05

Scope: the six P01 foundation packages on `greenfield/enterprise-microservices-plan`.
Examiner: Codex. This is a technical evidence examination, not an accountable G01
decision. The user's recorded G00 approval remains accepted.

**Correlated diagnostic telemetry and image admission pass.** The seven HTTP
applications and nine development candidates are verified at source
`36a14811b5afa23717566d5e8a08632e011f44a5`. BL-P01-002 remains resolved. P01 work and
verification remain IN_PROGRESS and G01 remains NOT_REVIEWED because repository
enforcement, actual operating inputs/integration and independent receiving
reviews are incomplete. No operated promotion or native effect occurred.

## Criterion examination

| Criterion | Measured foundation evidence | Remaining condition |
| --- | --- | --- |
| G01.01 — Independent builds | All seven applications and both selected workers pass isolated builds, package checks and image probes; EV-P01-028 binds current source, locks and image identities. | Accountable service/engineering review; requalify changed artifacts. |
| G01.02 — Isolated installation | EV-P01-029/030 retain 249 Compose and 266 Kubernetes checks, with authenticated diagnostics, isolation/recovery denials and 70 telemetry checks each. | Actual OP01 runtime/BOM/network/resource inputs and receiving review; diagnostic readiness is not product readiness. |
| G01.03 — Contracts and messaging | EV-P01-031 requalifies 28 HTTP fixtures at current source. EV-P01-027 retains 35 real PostgreSQL/RabbitMQ checks and 16 event fixtures at `b7705eef994c50863d87b4d8f9ff272f9397ca37`; their atomic rollback, deduplication and crash/restart scope is unchanged. | Independent architecture/quality review; business API semantics remain with feature packages. |
| G01.04 — CI and artifact trust | EV-P01-028 admits nine current images with 18 CycloneDX SBOMs, nine development signatures, 63 expected denials and nine unchanged-byte transfers. EV-P01-031 passes all 59 policy tests and the 10,187-file repository secret scan. | BL-P01-001: verified review accounts, default-branch hook, independent reporter and actual protection. OP02 operated registry/signer/trust integration. |
| G01.05 — Stateful identities | EV-P01-029/030 preserve database/runtime/migrator separation and TLS. EV-P01-027 retains 40 stateful-dependency checks, including revoked identities and persistent dependency state, at its recorded source. | OP03 actual secret/PKI/evidence custody, key/retention ownership and accountable security/database review. |
| G01.06 — Recovery and operations | EV-P01-031 repeats all 79 complete synthetic Permit Desk recovery checks. EV-P01-029/030 preserve shared-state/failed-deployment recovery and add correlated logs/spans/metrics, real buffer exhaustion, explicit loss and collection recovery. Each retains 30 resource samples across 15 containers with zero observed OOM kills; selected-object restore retains its earlier boundary. | Actual OP05 receiver/response review and telemetry integration, OP03 custody/loss/retention decisions, OP06 retained inventory/key recovery, OP07 support obligations and independent receiving acceptance. |

## Remediation and evidence integrity

The retained Bookworm failures remain historical evidence: four PHP images had
80 blocking matches each and five Python images had 63. The replacement study
measured zero blocking findings in the exact official Alpine 3.24.2 bases at the
same PHP/Python versions. Full PHP rebuilds exposed an incomplete OpenSSL upgrade
closure; the corrected lock includes the matching executable and libraries.
All 76 APK artifacts are pinned by URL/version/size/hash and each group was
installed into the exact base with networking disabled before adoption.

EV-P01-024 retains the initial passing remediation run 37272826276. Current
EV-P01-028 [run 37278732015](../../../verification/p01/artifact-trust/run-37278732015/retrieval.json)
again admits every candidate with zero blocking findings. Its 18 CycloneDX
image/source SBOMs remain hash-bound in the signed manifests. Nine signatures,
63 expected denials and nine unchanged-byte development transfers pass; retrieval
independently rechecked 206 raw build logs and 253 source bindings. The
[nine package results](../../../verification/p01/telemetry/packages/36a14811b5afa23717566d5e8a08632e011f44a5/report.json)
also pass, with 346 verified command logs, 388 artifact files and 412 unique source
bindings. Complete image layers are not retained and ephemeral development keys
are not an operated trust root. Later admission needs fresh scans and independent
full-artifact verification.

EV-P01-029/030 retain complete current runtime archives and exact report copies:
[Compose](../../../verification/p01/local/run-37278731868/report.json) and
[Kubernetes](../../../verification/p01/kubernetes/run-37278731990/report.json).
Retrieval verified 324/310 source bindings and 610/1,052 command logs respectively.
Each archive includes 22 telemetry snapshots and three signal exports, and both
campaigns cleaned up completely. The [telemetry record](../../implementation/p01-telemetry.md)
preserves both failed Kubernetes runs and their corrections; concurrent probes
remain in the collected population. Resource samples are point-in-time synthetic
measurements, not capacity or recovery objectives. Compose's effective limits
are explicitly unlimited; that observation does not approve an operating budget.
Replacement containers reset cumulative counters.

EV-P01-031 retains [current HTTP, Permit Desk, policy and repository-scan archives](../../../verification/p01/requalification/36a14811b5afa23717566d5e8a08632e011f44a5/report.json).
EV-P01-027 retains messaging, event and stateful-dependency evidence at its earlier
source; those campaigns are not relabeled as current-source runs. Secret detection
remains heuristic and does not inspect Git history. All declared source hashes
were compared with exact Git blob bytes at each recorded revision.

## Concrete receiving package

- [Current candidate set](../../../release/p01-candidate-set.json): zero held
  components; REQUIRES_INDEPENDENT_QUALIFICATION; promotion is not authorized.
- [Remediation record](../../implementation/p01-image-remediation.md) and
  [resource observations](../../implementation/p01-resource-observation.md), plus
  [correlated telemetry and collection recovery](../../implementation/p01-telemetry.md).
- [OP01–OP07](../../../release/operating-inputs.json): all seven remain UNKNOWN;
  `python3 scripts/p01/admission/operating_inputs.py --require-complete` returns
  HELD and exits 1. Schema validity does not supply actual inputs or acceptance.
- [Fresh repository settings](../../../verification/p01/admission/telemetry-settings-observation.json):
  unprotected branch and empty rulesets. The current connector supplies no
  settings-mutation operation; account permission does not add that capability.

Complete the remaining controls and independent reviews before changing G01's
decision. This technical examination makes no scope waiver or gate decision.
