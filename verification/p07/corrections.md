# P07 preparation observations and limitations

The preparation scope is E1: local commissioning metadata, exact plan/state/tool
record comparisons, bounded file handling and redacted errors. It has no native
adapter, credentials or execution path. Q05/Q06 have not run.

| Observation | Disposition |
| --- | --- |
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

The PostgreSQL image's [entrypoint source](https://github.com/docker-library/postgres/blob/master/docker-entrypoint.sh)
starts its temporary initialization server without a TCP listener; PostgreSQL's
[readiness tool](https://www.postgresql.org/docs/16/app-pg-isready.html) can target
TCP with an explicit host. These mechanisms support the diagnosed race; the actual
failure and subsequent campaign outcomes remain the evidence for this repository.
