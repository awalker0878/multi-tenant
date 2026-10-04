# Original final-code native and pilot evidence intake

The existing target-selection, version-provenance, campaign and native-dossier
owners decide qualification. `qualification.intake.FinalEvidenceIntake` fetches
and authenticates the original bytes behind their selected evidence. It never
runs a native command, issues support, updates active indexes or accepts a pilot.

Each directed campaign needs its own `MobilityCampaign`: source and destination
platform/product-tuple/selection/campaign IDs, migration method, exact guest
profile, original workload/job/plan, final code commit and actually installed
artifact digest. A reverse direction, different method, different guest,
different tuple or changed final artifact requires separate actual observations.
The unsupported matrix keeps all other rows held.

## Native observation contract

An enrolled independent observer retains its signed envelope as a
`VERIFICATION_RESULT` in the existing evidence repository. The campaign's
`evidence_ref` is that original event key and `artifact_sha256` is the SHA-256 of
the exact canonical envelope. The payload format is
`hosting-final-native-campaign-observation/1`, with these strict bindings:

| Binding | Payload fields |
| --- | --- |
| Exact directed campaign | `specificationSha256`, `routeId`, `endpoint`, `variantRef` |
| Exact native tuple and selection | `platform`, `productTupleId`, `productTupleSha256`, `selectionId`, `campaignId` |
| Exact original execution | `workloadId`, `jobId`, `planDigest`, `codeRevision`, `installedArtifactSha256` |
| Actual campaign procedure | `assertionId`, `observationClass`, `attemptId`, `procedureRef`, `result` |
| Independent chronology/custody | `observedAt`, `freshUntil`, `observerRef`, `executionOrigin`, `positiveControlEvidenceRef` |
| Original observed bytes | `observationEvidenceRef`, `observationArtifactSha256` |

`executionOrigin` must be `COMMISSIONED_NATIVE`; a local engine test or mocked
API remains local evidence. `productTupleSha256` hashes the exact current
dossier's canonical native product tuple, not just its human identifier. The
original observation artifact has format
`hosting-independent-native-observation/1`, the exact campaign digest/endpoint/
assertion, commissioned-native origin and nonempty actual measurements/native
responses. Its digest and original bytes must verify through independent
custody. Credentials, URLs and long raw logs remain outside bounded retained
receipts; retain reviewed opaque references/digests where needed.

A negative control also needs the exact same endpoint's earlier healthy positive
control, matching the campaign's original attempt ID and evidence reference.
Signed stale, failed, foreign-scope, altered-code and unsigned packets are held.
An observer signature cannot turn a locally relabelled fixture into native
evidence. No signer is supplied by the package.

After authentic original evidence exists, stage a protected review candidate:

```bash
python -m provisioner.qualification.intake --specification /etc/hosting/campaigns/exact-directed-campaign.json --endpoint source --attempt /etc/hosting/campaigns/exact-attempt.json --qualification-index /etc/hosting/qualification/native-index.json --directory /var/lib/hosting-campaign-review/unique-candidate
```

Configure the existing independent Object Lock/Vault evidence service and the
distinct observer/operating trust paths documented in the HA runbook.
`HOSTING_FINAL_EVIDENCE_ORGANIZATION_ID` and
`HOSTING_FINAL_EVIDENCE_TENANT_ID` select the independently commissioned evidence
workspace. The staging result is
`ORIGINAL_BYTES_VERIFIED_AWAITING_QUALIFICATION_OWNER_REVIEW`; active indexes
remain unchanged. The qualification owner reviews the current dossier and its
separate provenance/action/profile evidence through the existing owners. Native
execution still needs current contact/change authority, operating prerequisites,
instance handover, B48 scoped handover, B10 grant and native registry gates.

## Pilot and release

For every existing `PILOT_SCENARIOS` item, the independent observer retains a
`hosting-final-pilot-scenario-observation/1` signed payload. It binds the actual
scenario, final commit/artifact/support-matrix digest, receiving team, change
authority, observer, current observation window and `COMMISSIONED_PILOT`
origin. It points to exact retained
`hosting-independent-pilot-observation/1` bytes containing the actual operator/
service observations. The receiving team/change owner separately signs
`hosting-pilot-acceptance/1`, referencing the original six scenario envelopes.
Pilot acceptance cannot precede the observations it accepts.

`qualification.release.prepare` now requires the concrete `FinalEvidenceIntake`
owner. It first reassesses every advertised route against the current existing
dossiers, then fetches and verifies every required original native observation
and every pilot scenario. Missing original bytes or observer trust holds release
even when index metadata appears complete. Observer, receiving/pilot and release
keys are distinct, including their actual Vault mount/key paths in installed
composition. The release owner signs the final artifact/support/pilot digests;
the output is prepared for publication and grants no production authority.

```bash
python -m provisioner.qualification.release prepare --archive /var/lib/hosting-release/exact-runtime.whl --specification /etc/hosting/campaigns/exact-directed-campaign.json --pilot-acceptance /etc/hosting/campaigns/original-pilot-acceptance.json --qualification-index /etc/hosting/qualification/native-index.json --provenance-index /etc/hosting/qualification/provenance-index.json --campaign-index /etc/hosting/qualification/campaign-index.json --selection-index /etc/hosting/qualification/target-selection-index.json --directory /var/lib/hosting-release/unique-prepared-release
```

The receiving installation verifies both release and independent pilot
signatures, archive bytes and retained support/pilot digests with
`release verify-artifact`. The actual runtime separately validates the accepted
wheel, source tree and executable identity before every mutation. Current native
qualification must still be rechecked at execution time.

After old paths are deleted or any affected implementation changes, install the
new exact artifact and rerun each affected direction/method/profile campaign and
the pilot scenarios before preparing its release. Repository tests, generated
run sheets, staged review candidates and an older signed package cannot close
the new final-code campaign or receiving-team acceptance.
