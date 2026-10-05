# G01 engineering assessment — 2026-10-05

Scope: the six P01 foundation packages on `greenfield/enterprise-microservices-plan`.
Examiner: Codex. This is a technical evidence examination, not an accountable G01
decision. The user's recorded G00 approval remains accepted.

**Image admission is now passing.** BL-P01-002 is resolved for the nine remediated
development candidates at `b7705eef994c50863d87b4d8f9ff272f9397ca37`. P01 work and verification
remain IN_PROGRESS and G01 remains NOT_REVIEWED because repository enforcement,
actual operating inputs, remaining signal integration and independent receiving
reviews are incomplete. No operated promotion or native effect occurred.

## Criterion examination

| Criterion | Measured foundation evidence | Remaining condition |
| --- | --- | --- |
| G01.01 — Independent builds | All seven applications and both selected workers pass isolated builds, package checks and image probes; EV-P01-024 binds current source, locks and image identities. | Accountable service/engineering review; requalify changed artifacts. |
| G01.02 — Isolated installation | EV-P01-025/026 retain 179 Compose and 196 Kubernetes checks on the Alpine replacements, with authenticated diagnostics and isolation/recovery denials. | Actual OP01 runtime/BOM/network/resource inputs and receiving review; diagnostic readiness is not product readiness. |
| G01.03 — Contracts and messaging | EV-P01-027 requalifies 35 real PostgreSQL/RabbitMQ checks, 16 event fixtures and 28 HTTP fixtures; earlier detailed records preserve atomic rollback, deduplication and crash/restart scope. | Independent architecture/quality review; business API semantics remain with feature packages. |
| G01.04 — CI and artifact trust | Nine current images pass admission, with 18 CycloneDX SBOMs, development signatures, exact-artifact denials and immutable copies. All 59 policy tests and the 9,806-file repository secret scan pass. | BL-P01-001: verified review accounts, default-branch hook, independent reporter and actual protection. OP02 operated registry/signer/trust integration. |
| G01.05 — Stateful identities | Remediated runtime campaigns and EV-P01-027 preserve database/runtime/migrator separation, TLS, revoked identities and persistent dependency state. | OP03 actual secret/PKI/evidence custody, key/retention ownership and accountable security/database review. |
| G01.06 — Recovery and operations | Complete synthetic Permit Desk recovery, selected-object restore, shared-state persistence and failed-deployment recovery are requalified. Both environments now retain 30 resource samples across all 15 containers with zero observed OOM kills. | Correlated application signals and collection-failure coverage; actual OP05 receiver/response review, OP06 retained inventory/key recovery, OP07 support obligations and independent receiving acceptance. |

## Remediation and evidence integrity

The retained Bookworm failures remain historical evidence: four PHP images had
80 blocking matches each and five Python images had 63. The replacement study
measured zero blocking findings in the exact official Alpine 3.24.2 bases at the
same PHP/Python versions. Full PHP rebuilds exposed an incomplete OpenSSL upgrade
closure; the corrected lock includes the matching executable and libraries.
All 76 APK artifacts are pinned by URL/version/size/hash and each group was
installed into the exact base with networking disabled before adoption.

EV-P01-024 retains run 37272826276: every candidate is ADMITTED_DEVELOPMENT with
zero blocking findings. Its 18 CycloneDX image/source SBOMs remain hash-bound in
the signed manifests. Nine signatures, 63 expected denials and nine unchanged-byte
development transfers pass; retrieval independently rechecked 206 raw build logs
and 231 source bindings. Complete image layers are not retained and ephemeral
development keys are not an operated trust root. Later admission needs fresh
scans and independent full-artifact verification.

EV-P01-025/026 retain complete runtime archives and exact report copies; source
bindings and declared log hashes were rechecked before retention. Samples are
point-in-time synthetic measurements, not capacity or recovery objectives.
Compose's effective limits are explicitly unlimited; that observation does not
approve an operating budget. Replacement containers reset cumulative counters.

EV-P01-027 retains the requalified contract, messaging, dependency, Permit Desk,
policy and repository-scan archives. Secret detection remains heuristic and does
not inspect Git history. All declared source hashes were compared with exact
Git blob bytes at the recorded revision.

## Concrete receiving package

- [Current candidate set](../../../release/p01-candidate-set.json): zero held
  components; REQUIRES_INDEPENDENT_QUALIFICATION; promotion is not authorized.
- [Remediation record](../../implementation/p01-image-remediation.md) and
  [resource observations](../../implementation/p01-resource-observation.md).
- [OP01–OP07](../../../release/operating-inputs.json): all seven remain UNKNOWN;
  `python3 scripts/p01/admission/operating_inputs.py --require-complete` returns
  HELD and exits 1. Schema validity does not supply actual inputs or acceptance.
- [Fresh repository settings](../../../verification/p01/admission/remediation-settings-observation.json):
  unprotected branch and empty rulesets. The current connector supplies no
  settings-mutation operation; account permission does not add that capability.

Complete the remaining controls and independent reviews before changing G01's
decision. This technical examination makes no scope waiver or gate decision.
