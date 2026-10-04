# Release process

Owner: delivery/SRE lead with product, security, qualification and receiving service owners. Related work: P01.04, P09, P10.06 and P11; R02, R13, R29–R35.

## Candidate preparation

Select the release scope from the supported operations and exact platform tuples. Identify the contributing service versions, workflow/activity compatibility, adapter/automation versions, contract versions, database migrations and deployment configuration. Use one immutable [manifest](release-manifest.md) to bind them.

Build and sign artifacts once, then promote the same digests through the approved environment sequence. A rebuild creates a different candidate even if its human version label is unchanged. Record SBOM/provenance and required artifact-policy checks; keep secrets and environment-specific credentials outside the release.

## Qualification impact

Compare the candidate with the previously evaluated set. Identify changes to behavior, platform/backend APIs, credentials, policy enforcement, guest/data transformations, retries/fencing, database state, workflow histories, evidence custody and deployment assumptions. Map each change to affected support records and campaigns.

Rerun affected tests at the appropriate evidence level. Reuse unaffected evidence only after a documented scope/compatibility review. A documentation correction alone need not invalidate native support, but a change in documented assumptions that alters the claimed operating conditions requires reassessment.

## Promotion and release gates

| Stage | Required result | Owner |
| --- | --- | --- |
| Build/integration | Locked artifacts, contract/domain checks, required scans, provenance and reproducible environment installation | Engineering/delivery |
| Native qualification | Exact-scope positive, negative, uncertainty and recovery observations for selected support tuples | Qualification/platform owners |
| Preproduction | Restore/upgrade/failure/load checks, incident procedures and receiving-team readiness | SRE/security/service owner |
| Pilot | Agreed application outcomes, bounded operating scope, observation period and support handover | Product/application/service owner |
| Publication | G10/G11 acceptance, manifest, support records, release notes and operating instructions agree | Release accountable owner |

Use the [promotion procedure](../operations/runbooks/promote-release.md). A phase gate does not replace production change authority, and production change authority does not establish native qualification.

## Compatibility and rollout

List permitted current/target combinations for API consumers, event schemas, databases, Temporal workers and site pools. Use expand/contract migration stages; retain compatible worker routing for running histories. Define the admission freeze/drain boundaries and safe pause points for jobs that cannot continue through a change.

Before rollout, establish rollback feasibility. Some schema/data or native effects require forward recovery; an older image is not a universal rollback. Preserve the prior approved artifacts/configuration and verify recovery dependencies before a rollout starts.

## Withdrawal and correction

If qualification expires, a critical trust assumption fails or an unsafe effect is observed, suspend affected support records and stop new admission for that scope. Preserve observations and already dispatched operation outcomes. Decide containment and recovery with the service/application owners rather than silently resubmitting work.

Publish a corrected release or narrow the supported scope through an explicit decision. Record superseded manifests and the reason for withdrawal. Never rewrite old evidence to make it appear to have tested the correction.
