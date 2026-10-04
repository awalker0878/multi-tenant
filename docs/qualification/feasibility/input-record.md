# P00 input record and completeness check

[p00-input-record.json](p00-input-record.json) turns the existing RT01–RT10 and IP01–IP07 handoff into individual fields. [p00-input-schema.json](p00-input-schema.json) defines their structure. The [route review](../../implementation/p00-route-and-operations-review.md) and [decision and input review](../../implementation/p00-decision-and-input-review.md) remain the source of the requirements; this record introduces no new gate or approval. It distinguishes the approved VMware → OpenStack rebuild/restore baseline from unknown installed facts, complete fixture evidence and native authority. Credentials and native endpoints are not recorded here.

The [G00 accountable decision](../gate-reviews/g00-user-decision-2026-10-04.md) now supplies five observed and accepted baseline fields: direction, method, G00 criterion reviewer, baseline dispositions and explicit later checkpoints. Their evidence points to the immutable decision commit. Acceptance is limited to its development/advancement scope; subject-owner facts and full operational or native inputs are still recorded only when actually supplied. The full input record remains incomplete, while G00 approval permits independent P01 work.

Run from the repository root:

```sh
python scripts/validate_p00_inputs.py --report /tmp/p00-inputs.json
python scripts/validate_p00_inputs.py --scope route --require-ready
python scripts/validate_p00_inputs.py --scope IP07
python -m unittest discover -s tests/documentation -p 'test_p00_inputs.py' -q
```

The default check succeeds for a structurally valid, truthful incomplete record. Its JSON report lists each missing field, current fact/review status and accountable role. Exit `1` means malformed or contradictory data; `--require-ready` exits `2` for otherwise valid incomplete selected inputs. `route` checks RT01–RT10. `IP01`–`IP07` select the existing handoff packages; `all` includes the broader operating and delivery decisions. Wider IP02/IP07 decisions do not become new prerequisites for unrelated route preparation. IP03–IP06 reuse RT field groups instead of requiring duplicate copies of native facts.

`route` completeness includes native tuple and authority inputs because it represents the entire RT handoff. It is not a prerequisite for generating or exercising a local synthetic fixture, compatibility work or other independently authorized engineering. G00.04 can use bounded E1/E2 feasibility observations at their actual scope; this checker does not change that criterion into full E3 native qualification. Read-only lab input is used where available, and any actual native campaign still needs its own current scope and authority.

## Recording actual inputs

Each field distinguishes `UNKNOWN` (no supplied fact), `PROPOSED` (an unaccepted choice), `OBSERVED` (a supplied fact or decision record) and `BLOCKED` (an observed incompatible finding). An explicit `false` is a supplied value, not missing information. A negative observation can complete a question without establishing that a route is feasible. Use `BLOCKED` when that finding makes the selected candidate incompatible. The readiness check never evaluates platform support from a label or Boolean.

For an observed field, supply a sanitized value, observation timestamp with timezone, actual observer, campaign and explicit opaque resource IDs, and immutable evidence identity. Use `RESTRICTED` as the value when the underlying content belongs only in protected custody. Do not put secrets, endpoint addresses or sensitive resource names in the value. The protected record must contain the actual information, including the permitted resource/effect scope and the existing bounded campaign window. For post-write recovery, the selected value is `source_return_with_reconciliation` or `target_forward_recovery`; the separate preservation-procedure field records the mechanism and known-write correctness contract.

An evidence item has `kind`, `uri`, `sha256` and `revision`. `protected` references use the opaque `evidence://<custody-id>/<artifact-id>` convention; this is a logical identifier resolved by the existing evidence-custody process, not a new service or network destination. `revision` is the immutable store version, and `sha256` identifies its bytes. Keep signed download URLs and credentials in their approved systems. `repository` references use `git://awalker0878/multi-tenant/<40-character-commit>/<path>` with the exact file digest and commit revision. An actual attributable owner decision or sanitized observation may be recorded in pinned repository evidence; it does not require a new protected-custody approval. Mere design text can support a proposal but cannot establish an installed tuple or owner acceptance. In either location, the source content must substantiate the recorded fact or decision. The validator checks reference syntax and recorded identity only: it does not fetch artifacts, inspect their contents, verify access, verify their bytes or authenticate a person.

Retain the actual review disposition, reviewer and time when review occurs. An accepted observation removes that field from the missing-input list. Role labels route outstanding work; they do not substitute for a reviewer. Unknown/proposed fields cannot be marked accepted, wildcard resource grants are rejected, and a `READY` claim cannot hide absent route inputs. The record's `claimed_input_readiness` concerns route-input completeness only. Supplied references still require accountable examination against their actual protected contents and current scope.

One observation or review record may cover multiple fields when its explicit scope supports them; reuse its immutable reference and actual review metadata. Field-level tracking does not require a separate meeting, approval or artifact for each field.

## Completion boundary

All reports explicitly return `authorizes_execution: false` and `establishes_feasibility: false`, even for complete inputs. The tool makes no native call, reads no credential and grants no permission. Input completeness does not establish a grant's validity at execution time, independent observer access, safe native effects or a passing G00.04. The [initial-route procedure](initial-route.md), RF01–RF11 observations, existing campaign authority and both recovery boundaries still govern actual work. G00 decisions remain with the accountable review process and canonical delivery register.

When facts arrive, update only the affected fields and owning ADR/specification, retain immutable supporting evidence, and rerun the selected scope. Do not replace unknown installed information with historical branch values, public version documentation or synthetic test metadata. No arbitrary expiry period is added: changed tuple, fixture, authority, recovery or operating inputs receive the existing scoped impact review and retest treatment.

The tests exercise missing versus unknown versus explicit false, unreviewed and incompatible observations, incomplete provenance, mutable/invalid references, wildcard authority, absent post-write recovery and contradictory readiness. Test identities and evidence digests are synthetic in-memory fixtures only and are never copied into the input record. They prove validation behavior, not lab facts or native feasibility.
