# Promote an immutable release

Procedure ID: OPS-PROMOTE. Owners: delivery and SRE; security reviews artifact trust; assurance/release owner reviews support impact. Scope: R02/R31/R32/R35; P01.04 and P10/P11; Q09. Applies to transferring a reviewed artifact set into the next permitted environment without rebuilding it.

## Inputs and stage authority

Record source/target environments, release manifest digest/source revision, build provenance, component images/packages, SBOMs/signatures, dependency locks, configuration schema/revision, trust-verification policy, restricted-network requirements, promotion owner and change/campaign reference.

| Destination | Evidence and permitted scope |
| --- | --- |
| Development/integration | Required build/contract/provenance checks and isolated synthetic scope; no production credentials or support claim |
| Native qualification | Compatible integrated artifacts, explicit isolated campaign scope/authority, commissioned tuple and applicable safety controls |
| Preproduction | Representative topology/configuration, selected qualification evidence and required install/upgrade/recovery/security exercises |
| Production pilot/production | Applicable G10/G11 criteria and receiving-owner acceptance for the specific stage, current exact supported tuples, approved deployment/change conditions |

Apply the authoritative [gates](../../implementation/gates.md) to the destination. Production pilot evidence contributes to final release acceptance; do not require an invented prior successful pilot to initiate the separately authorized pilot. Promoting to an earlier environment never asserts later gates passed.

## Verification before transfer

The current P01 [candidate set](../../../release/p01-candidate-set.json) is HELD
and cannot enter this procedure as an approved release. Its development
signatures and successful quarantine copies do not override image findings,
missing operated trust or repository review. See the
[G01 assessment](../../qualification/gate-reviews/g01-engineering-assessment-2026-10-05.md).

1. Fetch the exact candidate manifest from the approved source and verify its authenticity against independently configured trust policy. Reject absent, untrusted or revoked signatures.
2. Resolve every referenced artifact by digest. Compare signed provenance, source/build revision, dependency lock and SBOM references. A matching tag/name is not a content check.
3. Confirm the complete dependency closure is available through approved registries/mirrors: runtime images, charts/manifests, packages, providers, conversion utilities, guest images and trust/recovery dependencies required for this release/mode.
4. Evaluate required secret/dependency/image/security checks and recorded risk decisions. Missing mandatory evidence blocks promotion; a report file without a result for the candidate digest is insufficient.
5. Check service/API/event/schema/worker/dependency compatibility and documented upgrade/rollback limits for the actual installed source version.
6. Review changed artifacts/configuration/tuples against current qualifications and plans. Assurance records required reruns or narrowly justified reuse; do not inherit support from a similarly named release.

## Transfer and target registration

| Step | Operator action | Expected observation |
| --- | --- | --- |
| Transfer | Copy only approved immutable artifacts and required verification material through the selected permitted path | Target bytes resolve to the same digest as source; no rebuild or hidden dependency download |
| Verify in target | Repeat digest/signature/trust checks using target policy and available revocation information | Target independently accepts provenance; missing freshness/trust cannot silently bypass validation |
| Bind configuration | Render schema-valid non-secret target configuration and protected secret references; compare to reviewed revision | Environment-specific values recorded separately from artifact identity; no embedded credentials |
| Assess stage readiness | Verify destination gates, installation/upgrade prerequisites, support impact and current ownership | All mandatory conditions met for this destination only |
| Register candidate | Record target artifact availability, manifest/configuration references and bounded intended deployment scope | Candidate is available for the [install](install.md) or [upgrade](upgrade.md) procedure; native admission remains separately controlled |

Where network isolation prevents fresh trust or revocation checks, use the explicitly selected time-bounded offline verification policy and record its age/limits. If no such policy exists or its bound expires, hold promotion. Copying a trust root beside an artifact cannot make that root independently trusted.

## Rejection and recovery

On digest mismatch, invalid signature, unknown source, incomplete closure, changed configuration or incompatible dependency, quarantine the candidate from deployment eligibility. Preserve hashes, verification output and origin references for diagnosis. Do not repair signed contents in place or rebuild only one artifact under the same release identity.

If an already promoted candidate is later found unsafe, hold its pending deployment and assess running environments separately. Security/assurance records affected artifacts and support claims; apply scoped admission holds where necessary. Use [rollback deployment](rollback-deployment.md) only after verifying persistence/workflow/native compatibility.

Never remove the currently working release or its required recovery artifacts merely because promotion failed. Keep old artifacts, verification material and decryption dependencies for the supported rollback/recovery and retention period.

## Evidence and completion

Capture source and target digest inventories, signature/trust policy revisions, provenance/lock/SBOM checks, closure verification, denied unsigned/altered-artifact test references, target configuration identity, gate references, qualification-impact review and accountable promotion decision.

Promotion completes when the target holds the verified candidate and its authorized stage record. Installation, native qualification, pilot activation and published supported release each require their separate procedures/evidence. Update the installed BOM only after deployment verifies what actually runs; artifact availability alone is not an as-built record.
