# G01 engineering assessment — 2026-10-05

Scope: the six P01 foundation packages on `greenfield/enterprise-microservices-plan`.
Examiner: Codex. This records technical evidence and remaining conditions. It is
not an accountable G01 decision. The user's existing G00 approval remains accepted.

**G01 is not ready to pass.** The register records P01 work as IN_PROGRESS and
verification as FAILED because mandatory real-image admission fails. G01 remains
NOT_REVIEWED. No native writes, operated promotion or new gate approval occurred.

## Criterion examination

| Criterion | Measured foundation evidence | Remaining condition |
| --- | --- | --- |
| G01.01 — Independent builds | Private locks and isolated package/image builds for seven applications and two workers; affected-owner selection, all package checks and contract checks pass at the resumed source. The complete candidate set binds source, locks and image identities. | Accountable service/engineering review; image security eligibility is separately held under G01.04. Future changed images need affected requalification. |
| G01.02 — Isolated installation | EV-P01-016/018 retain 149 Compose and 166 Kubernetes checks; scoped authenticated diagnostics, dependency failure, restricted paths and synthetic identity are measured. Permit Desk and stateful-dependency records retain their separate installation scope. | Review actual OP01 environment/BOM/network inputs before adopting an operated runtime; do not treat diagnostic readiness as completed product behavior. |
| G01.03 — Contracts and messaging | EV-P01-015/017 retain 35 real messaging checks, 16 event fixtures and 28 HTTP fixtures, deterministic clients, version freezing, rollback, deduplication and crash/restart observations. | Independent architecture/quality review; business API semantics and future capabilities remain with their owning feature packages. |
| G01.04 — CI and artifact trust | EV-P01-019–023 retain policy/exclusion/impact controls, actual target-base non-execution, real scans, SBOMs, provenance, signatures and exact-artifact denials. The expanded 59-test suite and repository secret scan pass. | FAILED candidate admission: every image remains held. Actual review accounts, default-branch hook/reporting/protection activation and OP02 operated registry/signer/trust integration remain absent. |
| G01.05 — Stateful identities | Context runtime/migrator separation, denied foreign/admin access, TLS, revoked identities and persistent dependency state are measured in EV-P01-014/016/018. | OP03 actual secret/PKI/evidence custody and key/retention ownership; accountable security and database review. Disposable credentials are not operated identity integration. |
| G01.06 — Recovery and operations | Complete synthetic Permit Desk restores, selected retained object recovery, persistent Console sessions/cache, failed-deployment recovery and seven synthetic HTTPS alert receipts are retained. | Actual OP05 receiving route/response acknowledgement, OP06 retained inventory/key recovery and receiving review. Reconcile remaining correlated signal/resource measurement coverage and OP07 support obligations. Synthetic acknowledgements are not human or service acceptance. |

## Artifact findings and evidence integrity

The corrected image campaign at `41bbcaec3be5ec0f2abdd534bab2041e46a74e90`
contains the exact fixed libpcre2/tzdata packages and removes unused PHP kernel
headers. Each of four PHP images still has 80 blocking package/advisory matches
(36 distinct advisory IDs); each of five Python images has 63 (23 distinct IDs).
No fixed version is reported for those remaining matches. These are scanner
observations requiring triage, not exploitability determinations. No exception is
active. BL-P01-002 owns the explicit remediation/requalification work.

All nine image control campaigns pass their negative cases while keeping the
candidates HELD. There are 81 denial observations and nine byte-identical copies
into quarantine. This is not a successful product promotion. New run 37269433149
at `48a998c8b4517f5d27933973d9d4b04677b48e49` again reports PASSED_CONTROLS/HELD
for all nine images, with no campaign errors. Its
[observed job summaries](../../../verification/p01/artifact-trust/run-37269433149/workflow-observation.json)
keep that distinction explicit.

The [retention repair](../../implementation/p01-evidence-retention.md) restores
18 original build logs through verified Git blobs. Their original SHA-256 values
were never changed. The continuous checker verifies declared retained inventories;
it establishes byte consistency, not independent authorization or authenticity.

EV-P01-023 retains run 37269433140: 59 control tests, a successful detector positive
control, and zero secret findings across all 9,766 tracked files. Both downloaded
archive hashes and every source binding were independently compared with the
immutable Git tree. The original redacted report remains in its verified ZIP.
Heuristic scan coverage does not prove secret absence or examine Git history.

The [resumed workflow summary](../../../verification/p01/policy-controls/resumed-workflow-summary.json)
at source `48a998c8b4517f5d27933973d9d4b04677b48e49` records successful package,
contract, policy, documentation, Compose, Kubernetes and Permit Desk workflows.
The image workflow is the single failed workflow, for the explicit nine-candidate
security hold described above. All workflows completed; none remains running in
this source-bound validation set.

## Concrete receiving package

- [Complete held candidate set](../../../release/p01-candidate-set.json): all nine
  image/source/lock/SBOM/provenance/signature bindings and denial observations.
- [OP01–OP07](../../../release/operating-inputs.json): actual inputs, accountable
  roles and immutable evidence fields; all seven remain UNKNOWN. Run
  `python3 scripts/p01/admission/operating_inputs.py --require-complete` to observe
  the current failed readiness result. A schema-valid record is not authorization.
- [Admission activation record](../../implementation/p01-operating-inputs.md):
  verified account mapping, independent exact-PR reporter, default-branch hook,
  CODEOWNERS and effective settings/denial observations still required. The
  [latest settings observation](../../../verification/p01/admission/resumed-settings-observation.json)
  remains `protected: false` with rulesets `[]`. The available connector exposes
  no settings-mutation operation; administrator account permission does not add one.

Resolve the stated failed/missing conditions and record receiving reviews before
changing G01's decision. An accountable decision to change scope or carry work
forward must be recorded explicitly; this examination makes no such decision.
