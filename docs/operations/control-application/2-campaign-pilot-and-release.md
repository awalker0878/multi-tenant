# Selected mobility campaign, final-code pilot and release

Repository implementation, native route qualification, operating acceptance and
production authority remain separate. The installed control driver currently
implements only VMware to OpenStack application rebuild/restore for the exact
`linux-ubuntu-2404` guest profile. Other directions, guest releases, cold/warm
whole-VM, same-family relocation and database-sync methods stay unavailable
until their native drivers and separate current evidence exist.

## Guided first-route campaign

Use `MobilityCampaign` and `CampaignEndpoint` from
`provisioner.qualification.mobility` to create a strict campaign specification:
exact source/destination selected tuples and campaign IDs, direction, method,
guest profile, discovered application/workload, admitted job and plan digest,
final source commit and installed artifact SHA-256. `python -m
provisioner.qualification.mobility run-sheet <protected-specification.json>`
produces the procedure list without native contact or approval.

The resulting `variantRef` binds every retained observation to that exact
specification. Follow the authorized contact/run sheets under the existing
target-selection/campaign owners, using independent observers and native
authority from the selected site. Complete prerequisite authority, privilege,
scope, stale/revoked and recovery negatives before controlled native writes.
Exercise isolated rehearsal, interrupted accepted operations, persistent
source-writer exclusion, final consistency/integrity, useful application service,
measured traffic cutover and both prewrite and committed-data postwrite recovery.
Retain source/cleanup decisions under separate retirement authority.

Export observations into the existing campaign evidence index with the exact
assertion IDs/classes and `variantRef`. Negative controls require an earlier,
still-healthy passing positive control. The native qualification owner separately
reviews and issues a current exact-tuple dossier containing the same evidence
references, digests and observation times. The campaign export cannot issue its
own qualification.

`python -m provisioner.qualification.mobility assess <specification.json>`
selects only current independent campaign/dossier evidence for that exact route.
The reviewer may supply independently administered current index paths. Code,
direction, method, guest, scope, selected tuple, job or artifact changes invalidate
the variant; source/target campaign evidence does not reverse automatically.
Current evidence cannot supply a missing native implementation.

Before each actual effect, `SelectedQualificationGate` rereads the existing
current qualification/provenance/campaign/target/capacity indexes. Their exact
canonical `bundle_digest` is the selected artifact's `qualificationDigest`.
Both directed tuples require current exact guest-profile dossiers. Each selected
action requires `ACTION_<operation-kind>` with its independent retained native
evidence and `action_variant(selection, operation_kind)`. The destination must
also have a current commissioned envelope at its exact site. Guest configuration,
policy changes and quota changes have distinct action kinds and capabilities;
VM power authority cannot authorize them. B07/B10 worker credentials,
ownership/epochs and operating acceptance are rechecked independently.

## Directed expansion

`directed_mobility.expansion_assertions` adds method-specific capture/chain,
device/encryption negatives, isolated converter/import/boot, actual distinct
topology moves, database commit/lag/divergence and warm-state requirements.
Enterprise wave dependency/fairness/budget/stop assertions apply only to an
explicit wave campaign; a single-job success cannot satisfy concurrent-wave
qualification. `unsupported_matrix` preserves all directed method and special
guest rows with their current blockers, including reverse and same-family cases.

`provisioner.execution.image_sandbox` provides fixed retained-disk inspection
and conversion behind mandatory bwrap namespaces and prlimit budgets. It verifies
reviewed binary digests, copies a bounded standalone image into a fresh private
directory, mounts it read-only, removes ambient credentials/capabilities/network,
and invokes only fixed qemu-img info/convert commands. Unknown/encrypted/backing
chains, changed digests, unavailable tools or unavailable namespace enforcement
hold. Conversion produces a disk artifact; it does not capture/export a running
VM, import/boot a guest or establish whole-VM route qualification. B38 requires
those separate native owners and observations.

## Retained state and final-code pilot

Rehearse the one-time retained-state conversion through its owned importer and
independently reconcile original counts/digests/native IDs and old-writer drains.
Keep imported state observation-only. Delete superseded paths only after their
consumer/state migration is verified; rerun every affected native campaign on
the resulting final source/artifact. Qualification at an earlier revision cannot
accept those deletions or changed histories.

`provisioner.qualification.release.pilot_run_sheet(spec)` lists discovery/review,
guided provisioning/migration, interruption/containment/recovery, alert delivery
and operator ACK, observation restore/upgrade, and actual receiving-team/first-wave
handover scenarios. They start NOT_RUN. Actual sysadmins, change authority,
receiving service owner and independent custody must supply those observations.
There is no automatic acceptance or fixture-to-pilot promotion.
`python -m provisioner.qualification.release pilot-run-sheet --specification
<protected-specification.json>` produces those NOT_RUN scenarios for an operator.

The receiving operating authority signs `hosting-pilot-acceptance/1` with exact
final revision/artifact/support-matrix digests, authority/acceptance references,
current acceptance/review instants and every accepted scenario's retained evidence
reference/digest. Its signature is independently verified with the separately
trusted acceptance key. No unsigned Boolean can make a pilot accepted.

## Supported release preparation

`release.prepare` revalidates each advertised route using the existing current
native chain, hashes the actual runtime archive, retains all unsupported matrix
rows, and verifies current signed final-code pilot acceptance before using the
release owner's signer. It writes the signed manifest, support matrix and original
pilot envelope into a fresh private release directory. It does not publish
remotely or grant production authority. `release.verify_artifact` checks the
signed manifest and exact runtime/support/pilot bytes before offline installation;
native action qualification must still be current at execution time.
The installed release module also exposes `prepare` and `verify-artifact` modes.
`HOSTING_PILOT_ACCEPTANCE_VAULT_TRUST_JSON` and
`HOSTING_RELEASE_VAULT_TRUST_JSON` select distinct reviewed owner keys; neither
may overlap checkpoint custody. The verify-only credential is read from
`HOSTING_RELEASE_VERIFY_TOKEN_FILE`; preparation additionally requires
`HOSTING_RELEASE_SIGN_TOKEN_FILE` and `HOSTING_RELEASE_KEY_ID`. Missing or
withdrawn owner custody holds, and neither mode contacts a native platform.

Install the exact reviewed distribution/resources and its approved dependencies
through selected artifact custody. Apply immutable database migrations using the
separate migration owner after rehearsal. Drain and fence workers before upgrade;
reconcile Temporal build-version routing, existing accepted jobs and high-water
marks before starting new writers. For rollback, restore only into an isolated
observation database and preserve newer independent evidence/target writes until
explicit recovery decisions. Reverting package bytes alone cannot roll back
committed target application data or revive old writer authority.

External holds remain exact installed endpoints/versions, independent observers,
current scoped native privileges, commissioned resources, actual operating and
recovery campaigns, receiving-team pilot acceptance and release signing custody.
No B37/B47 native campaign, B49 pilot or B50 supported operating release is claimed
complete by this repository increment.
