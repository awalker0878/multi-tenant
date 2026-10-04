# Qualification campaign template

Record campaign ID, requirement/package/gate IDs, owner/independent reviewer and whether this is a proposed test design or executed campaign. Select evidence levels from the requirements register.

## Exact scope

Identify source/target platform versions, backend/features, operation/direction/method, guest/image and data profile, network/security/service topology, failure assumptions and product/adapter artifact revisions. Specify included and excluded support claims.

## Authorization and preparation

Record the isolated test environment, campaign authorization, credential/resource scope, dataset classification, impact limits, recovery readiness and stop/revocation mechanism. Reference protected details; do not place them in Git.

## Cases

For each stable test ID specify prerequisites, action/fault, independently observed expected result, denied behavior, integrity/security checks, recovery path and evidence artifact. Cover normal, partial, duplicate, concurrent, interrupted, revoked and uncertain outcomes applicable to the capability.

## Results and qualification

Store actual immutable evidence with digests, revisions, observations, limitations, reviewer and expiry/retest triggers. Report missing and failed cases. Qualification requires independent review of the complete scope and updates the evidence-backed support claim; test design or activity completion alone is insufficient.
