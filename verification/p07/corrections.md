# P07 preparation observations and limitations

The preparation scope is E1: local commissioning metadata, exact plan/state/tool
record comparisons, bounded file handling and redacted errors. It has no native
adapter, credentials or execution path. Q05/Q06 have not run.

| Observation | Disposition |
| --- | --- |
| Kubernetes run `37545566682` returned exit 0 with empty stdout from the Console shared-state PHP probe, then failed strict JSON parsing. The original copied file bytes were not measured, so the original cause cannot be established from that output alone. | Preserve artifact `11450158762`, SHA-256 `e125c16776e6a6b134c5af365c64079b59a9e92a8a74a9939c85423b03602421`. Transfer public probe bytes as encoded argv, verify the installed SHA-256, and provide the stage through a local pipe inside the container. Keep strict JSON parsing and every session/cache/lock assertion; rerun the affected Kubernetes campaign. No native/product pass is inferred from the failed probe. |
| The P06 push filter omitted Inventory, Catalogue and shared P04/P05 fixture inputs used by its live campaign, so the corrected Inventory manifest did not trigger P06. | Include these consumed source paths and rerun on the corrected source. Keep earlier behavior passes separate from exact-source qualification. |
| All three corrected live campaigns passed behavior checks, but independent source-hash comparison found Inventory's tracked `SOURCES.txt` missing the already present Planning interface/application modules. Frozen installation regenerated that manifest before the campaign's source snapshot. | Reproduce the generated manifest with the locked build environment: SHA-256 `0678ba79c585728c27d8034067de0c5bbc7ec3fd80af8c5ff9046813615cc351`. Publish those two missing entries. Preserve original reports and the explicit source discrepancy; compare every measured source byte and rerun affected qualification on the corrected source. No product module is added or changed by this metadata fix. |
| Context-policy run `37544824899` found the correction record's review-packet link before that packet was published. | Publish the already prepared packet in the following documentation commit and rerun clean-source link checks. The failed run remains recorded. |
| Firefox campaign run `37544177753` at `249a77e` failed before Temporal started: schema setup received PostgreSQL `57P03` while the database was starting. The fixture's Unix-socket health query could succeed against the temporary initialization server. | Preserve original artifact `11449950917` (SHA-256 `d5e6037ef0ff64e43d76ffd171f63770bb8fc3b645ea3f98c36616a1b0c03e37`). Change only the P06 Temporal fixture health check to wait for the final TCP listener. Rerun all three live campaigns; the original failure remains failed. |
| Initial local lint/type passes found long lines, compact test formatting and an imprecise variadic-tuple annotation. | Corrected before the respective source commits; final strict Ruff/mypy checks independently pass. |
| The initial local full Lifecycle run passed 129 tests and skipped five PostgreSQL-dependent cases without a PostgreSQL setting. | Retained as limited local verification, not a database pass. |
| Supplying the locally available PostgreSQL binary then produced five fixture setup errors: the container could not `chown` the disposable database directory to UID 65534 (`EINVAL`). | No product assertion ran for those cases and no native result is inferred. Do not weaken the unprivileged database fixture. Use the real PostgreSQL GitHub-hosted P06 regression campaign; record that result separately. |
| The first installed-CLI smoke reached the strict commissioning hold, then its parent fixture generator lacked `pytest`. | Preserve the partial logs under `final/installed-cli-initial/`; rerun using the locked Lifecycle test interpreter for generation. The separately installed child remains isolated and passes both matching and changed-byte comparisons. |
| The first documentation attempt scanned an installed `.venv` and reported broken links inside third-party Temporal package material. | Run documentation/architecture checks on a clean source-only snapshot, as hosted CI does. Do not change product/documentation checks to ignore legitimate failures. |

The final preparation report retains command logs, exact source bindings, test XML
and the strict input checker result. Its valid `HELD` commissioning response is an
expected outcome of absent real inputs. A passing checker campaign does not mark
the native input packet ready or any P07 package complete. The register and
[remaining review packet](../../docs/implementation/p07-completion-review.md)
keep the unimplemented native outputs and receiving obligations explicit.

Final execution regression run `37545874970` at
`c2c29067f0ecdb7d0df0c92687507b66415219e5` passes all 243 core tests and all
148 checks in each of Chromium, Firefox and WebKit. Independent comparison now
matches every measured source byte, including the regenerated Inventory manifest.
All command and artifact hashes match. Original archives and the three earlier
one-file discrepancies remain separately identified in the final index; none is
silently converted into a source-qualified pass. This closes the identified
regression defects, without supplying any missing P07 native observation.

Corrected Kubernetes run `37546672554` at
`b0f5516409dd4047c3c25eb0ba0861f76d321c11` passes 271 checks, including all
five verified probe transfers and the existing shared session/cache/lock checks.
All 103 installation source bindings and 445 command-stream pairs match;
cleanup succeeds. The associated [workflow receipt](final/regression-completion.json)
records all twelve preparation/regression workflow passes with their own source
revisions. The original empty-output failure remains retained and failed.

The PostgreSQL image's [entrypoint source](https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh)
starts its temporary initialization server without a TCP listener; PostgreSQL's
[readiness tool](https://www.postgresql.org/docs/16/app-pg-isready.html) can target
TCP with an explicit host. These mechanisms support the diagnosed race; the actual
failure and subsequent campaign outcomes remain the evidence for this repository.


## Native workflow-control continuation

The expanded native campaign at `62a10992ea09677092c289ec3972f1646b7883f7`
failed one test assertion: an extra caller-controlled worker identity is correctly
rejected as malformed input with HTTP 422, while the new test expected 409.
The product rejection was unchanged. `e4ce3f4b1416845aa35735315d0f758ef845bf7a`
corrects that assertion; the complete campaign is repeated. The original failed
archive, report, test XML and command logs remain under
[native-workflows](native-workflows/qualification-index.json), with their original
FAILED result. The initial passing control-core campaign is retained separately.

Local persistence setup again encountered the known UID/chown EINVAL limitation.
No database assertion from that local attempt is claimed as passing; hosted
qualification requires both service and worker PostgreSQL tests without skips.

The isolated worker package campaign at `62a1099` also found a test packaging
error: its golden request was read from the repository-level contract directory,
which is deliberately unavailable in the isolated component copy. Preserve the
original `p07-isolated-worker-initial-62a1099.zip` archive. `880db145e2d90e0be6b23f7a744f592cf6af233f`
keeps a private fixture inside the worker's test inputs, and the authoritative
contract campaign verifies that it exactly equals the published fixture. The
worker's 93 saved-plan/authority tests pass from an isolated local copy. No
package boundary or required test is relaxed; hosted package verification repeats.

Final source `880db145e2d90e0be6b23f7a744f592cf6af233f` passes the complete
P07 campaign (253 Lifecycle and 142 worker tests, zero skips, all 18 commands),
the isolated worker package and P06 core plus all three live browser journeys.
All six original component/package archives remain retained with verified source,
command and artifact hashes. The [regression receipt](native-workflows/regression-completion.json)
records the remaining workflow passes and each run's actual source. No failed
record is relabelled and no P07 native result follows from these regression passes.
