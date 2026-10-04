# CI retirement regression and package-source attribution repair

Reviewed 2 October 2026. Continue B01 and B05 verification from
`c5a579fa3a33a4c1bf0bceb33a18bee500872aba` on `implementation/all-waves`.
The [B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md)
remains the sole backlog. This is a verification repair, not a new runtime, release
approval or native capability.

## Baseline failure, not a pending check

Architecture run `36959383458` completed with failure in repository job
`110689442695`. Its retained `repository-local-test-reports` artifact
`11207730828` records 4,274 tests, two assertion failures and 123 skips.
Both failures were in `tests/test_retired_interfaces.py`: the expected map still
contained seventeen retirements, while the reviewed register correctly contained
eighteen after retiring the Terraform catalog module. The complete seven-test
retirement suite reproduced the two failures locally before correction.

The prior package, Terraform, Ansible, control-plane and Temporal job successes do
not turn that overall architecture run into a pass. The original report and failed
reproduction remain evidence. Rechecking the final revision is required.

## Independent expectations and rejection tests

The test's explicit `EXPECTED` map now includes `provisioner/execution/terraform_catalog.py` with
replacement `provisioner/execution/terraform_catalog.py`. It remains independent
of the actual register, retaining exact name/kind/replacement and duplicate checks.
The existing register itself does not change and still contains eighteen entries.
Reintroduction tests cover every retired path; malformed-register and retired-text
negative tests are unchanged. Real-owner checks now also inspect the execution
package, ensuring the replacement contains implementation and does not import
back into `tools` or `scripts`.

This is not permission to delete an active runtime owner or retained state. The
existing `provisioner/execution/source_integrity.py` and every caller remain unchanged in this delivered
increment. A separately prepared source-integrity relocation was not published;
no partial migration, forwarding alias or extra retirement is included here.

## Test-source attribution follows package ownership

The regression runner's `source_snapshot(root)` helper now includes `provisioner/`
and `hosting_resources/`, plus `pyproject.toml`, `setup.py` and `MANIFEST.in`.
Previously, the recorded source map listed legacy tool families but omitted these
package owners and build inputs. The new map is used by the same existing report
writer; there is no second report format or alternate test runner.

Two new regressions verify exact hashes of actual package/build inputs, attribution
of the still-active integrity tool, absence of the retired catalog tool, exclusion
of bytecode/provider caches, and changes to a package file in a disposable non-Git
source tree. Original manifests are not rewritten. The broader coverage naturally
changes new manifest counts/digests and must not be compared as identical to earlier
narrower maps. A digest map is not a signature, complete release inventory, dependency
lock, authority proof or evidence that every file was exercised by a particular test.

## Local verification and limits

The delivered scope passed the nine-test retirement/source-attribution suite,
63 Terraform-related regression tests and 25 golden-replay tests without skips.
Counts are independent suite observations and may overlap other wider runs. Final
publication and final-head CI results are recorded on draft PR 54 separately; this
record does not assert that a future run has passed.

An exploratory broad run on the separately prepared, unpublished relocation failed
on unavailable optional database/workflow packages, missing OpenSSH/pinned Ansible
and host-specific fixtures, including the existing nested-environment PyYAML failure.
It is not a passing baseline or verification of this delivered tree. Tests on the
delivered tree and its final CI must be identified separately. No dependency pin,
platform guard, required test, workflow permission or native safety check is relaxed.

## Architecture and remaining gates

The maintained architecture scope does not change: TAD-M01 remains 0.27, ICD-M01
0.26 and TRANS-M01 0.16, all Proposed. RAD-M01 remains 0.13 and solution records
remain 0.4. Their version metadata is not advanced for an unpublished runtime change.
B05's remaining owners and retained-state conversion, B17/B20 deployment/enrichment,
B22 fleet operations and the provisioning/migration/qualification waves remain open.
No deployed vendor environment or production dataset was contacted.
