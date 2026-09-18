# Appendix A — Canonical object contract and API surface

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13423_1645000677"></a>
<a id="app_A"></a>

The companion schemas are the exact machine-readable reference for field types, closed property sets, enums and conditional structural requirements. The following dictionary lists every object and every required spec field. References have kind, name and immutable semantic version. Objects use apiVersion: hosting.platform/v1.1, kind, metadata and spec; status is a separately authorized observed-state surface. \[[S30](77-appendix-h-primary-sources-and-implementation-references.md#S30)\]


<a id="source-table-806"></a>

| Envelope field | Meaning / write authority |
| --- | --- |
| apiVersion / kind | Versioned contract and object type; unknown versions/kinds are rejected |
| metadata.name / namespace / ownerRef / version | Stable named identity, administrative scope, accountable owner and immutable definition version |
| metadata.uid / generation / resourceVersion | Server-issued identity, desired-state generation and optimistic concurrency token |
| metadata.createdAt / deletionTimestamp / finalizers | Server lifecycle and controlled deletion obligations; not consumer-granted authority |
| spec | Desired fields defined by the exact object kind; unknown fields rejected |
| status | Controller-issued phase, observedGeneration, conditions, operation and evidence references; not a consumer input |
| Typed reference | {kind, name, version}; authenticated authorization and tenant/provider scope are evaluated independently of existence |

<a id="__RefHeading___Toc13425_1645000677"></a>

## Object definitions

<a id="kind_TenantNamespace"></a>

### TenantNamespace

Administrative scope. Quotas are illustrative entitlements, not measured available capacity.

Required spec fields: identityGroups, entitlements, quotas, lifecycle, securityAuthorityRef.

lifecycle = Requested \| Active \| Restricted \| Suspended \| Retiring \| Retired.

<a id="kind_SecurityProfile"></a>

### SecurityProfile

Impact levels and tailored control selection are separate from operational uptime. Empty control selection is legal only as a non-approved design example.

Required spec fields: confidentiality, integrity, availabilityImpact, catalogueEdition, controlSelections, mandatoryServiceProfiles, cryptographicProfileRef, evidenceProfileRef, approvalState.

confidentiality = Unclassified \| ProtectedA \| ProtectedB; integrity = Low \| Medium \| High; availabilityImpact = Low \| Medium \| High; approvalState = Proposed \| Approved \| Retired.

<a id="kind_AssuranceProfile"></a>

### AssuranceProfile

Dedicated scope is a vector; numeric values are local proposed examples.

Required spec fields: level, isolation, hostZoneSharing, requiredTests, maxEvidenceAgeHours, approvalState.

level = Standard \| Enhanced \| Dedicated; hostZoneSharing = single-zone \| approved-alternative; approvalState = Proposed \| Approved \| Retired.

<a id="kind_AvailabilityProfile"></a>

### AvailabilityProfile

Measured service SLO, not the availability-impact classification and not a delivered guarantee.

Required spec fields: sloPercent, measurementWindowDays, minimumFailureDomains, coveredFailureModel, maintenancePolicy, recoveryProfileRef, approvalState.

approvalState = Proposed \| Approved \| Retired.

<a id="kind_RecoveryProfile"></a>

### RecoveryProfile

RTO/RPO include the service-specific measurement boundary.

Required spec fields: rtoMinutes, rpoMinutes, exerciseIntervalDays, recoverySitePolicy, fencingRequired, bootstrapRunbookRef, failbackRunbookRef.

fencingRequired = true.

<a id="kind_BackupPolicy"></a>

### BackupPolicy

Retention is a proposed example. Successful restore is a mandatory acceptance outcome.

Required spec fields: retentionDays, immutableCopyRequired, isolatedAdministrationRequired, copyLocationPolicy, restoreTestIntervalDays, keyPolicyRef, holdOverridesDeletion.

isolatedAdministrationRequired = true; holdOverridesDeletion = true.

<a id="kind_CryptographicProfile"></a>

### CryptographicProfile

Algorithms are selected through an approved external policy; this sample does not invent a certification.

Required spec fields: guidanceEdition, transportPolicyRef, atRestRequired, moduleValidationPolicy, algorithmInventoryRef, keyPolicyRef, plaintextFallbackAllowed.

plaintextFallbackAllowed = false.

<a id="kind_KeyPolicy"></a>

### KeyPolicy

Rotation intervals need local approval; destroy only keys with proven exclusive eligible scope.

Required spec fields: ownerRef, custodyPolicy, kmsServiceProfileRef, rotationIntervalDays, recoveryPolicyRef, destructionApprovalRef, sharedKeyDestructionAllowed.

sharedKeyDestructionAllowed = false.

<a id="kind_ComputeProfile"></a>

### ComputeProfile

Compute requirements are independent of vendor VM identifiers.

Required spec fields: cpuArchitecture, minimumMemoryGiB, minimumVcpus, hostZoneSharing, secureBootPolicy, overcommitPolicy, imageProfileRef, antiAffinityRequired.

cpuArchitecture = x86\_64 \| aarch64; hostZoneSharing = single-zone \| approved-alternative.

<a id="kind_StorageProfile"></a>

### StorageProfile

Block, file and object profiles cannot be treated as interchangeable just because all store bytes.

Required spec fields: interface, minimumCapacityGiB, performanceClass, isolationPolicy, cryptographicProfileRef, backupPolicyRef, copyLineageRequired, exportFormatPolicy.

interface = block \| file \| object; copyLineageRequired = true.

<a id="kind_ImageProfile"></a>

### ImageProfile

Illustrative unapproved image. Zero digest is a sentinel, not a production artifact digest.

Required spec fields: artifactRef, artifactDigest, provenanceRef, baselineRef, vulnerabilityDispositionRef, retirementAt, approved.

<a id="kind_PlacementProfile"></a>

### PlacementProfile

Location and support constraints are independent facts; residency does not establish sovereignty.

Required spec fields: allowedSites, allowedPlatforms, dataLocations, controlLocations, supportAccessPolicy, keyCustodyPolicy, coResidencyPolicyRef, portabilityExtensions.

<a id="kind_EvidenceProfile"></a>

### EvidenceProfile

Evidence freshness follows change and profile scope, not simply a single timer.

Required spec fields: requiredTests, maxAgeHours, retentionDays, integrityPolicy, accessPolicy.

<a id="kind_FlowProfile"></a>

### FlowProfile

Raw firewall rule order and provider identifiers stay out of the consumer contract.

Required spec fields: protocol, ports, stateful, tlsRequired, mtlsRequired, l7PolicyRef, loggingProfileRef.

protocol = tcp \| udp \| icmp \| icmpv6 \| other.

<a id="kind_ServiceProfile"></a>

### ServiceProfile

Service endpoints are explicit; binding does not grant a shared subnet or management path.

Required spec fields: serviceType, flowProfileRef, endpointNames, providerScope, availabilityProfileRef, managementEndpointExposed.

serviceType = dns \| time \| identity \| logging \| backup \| kms \| pki \| monitoring \| other; managementEndpointExposed = false.

<a id="kind_SecurityDomain"></a>

### SecurityDomain

Logical authority, independent of site-specific native routing contexts. MZ is provider-only.

Required spec fields: zoneClass, authorityRef, tenantScope, assuranceProfileRef, sharingPolicy, addressPolicyRef.

zoneClass = PAZ \| OZ \| RZ \| HRZ \| MZ; sharingPolicy = exclusive-wsd \| same-authority-approved \| provider-service.

<a id="kind_SecurityDomainInstance"></a>

### SecurityDomainInstance

Provider-internal realization; a candidate platform cannot become Ready by passing schema validation.

Required spec fields: domainRef, siteRef, platformProfileRef, addressScopeRef, edgeAttachmentRefs, failureDomainRef.

<a id="kind_Network"></a>

### Network

Observed provider network; example prefixes are not allocations for a real environment.

Required spec fields: wsdRef, instanceRef, ipv4Prefix, ipv6Prefix, allocationRef, dhcpProfileRef, dnsPolicyRef, endpointSecurityPolicyRef.

<a id="kind_FlowIntent"></a>

### FlowIntent

Flow approval and path compilation are semantic operations, not inferred from this JSON alone.

Required spec fields: wsdRef, source, destination, flowProfileRef, direction, justification, validFrom, expiresAt, loggingRequired.

direction = source-to-destination \| bidirectional; loggingRequired = true.

<a id="kind_ServiceBinding"></a>

### ServiceBinding

Publishing a service and authorizing a consumer binding are separate decisions.

Required spec fields: wsdRef, consumerDomainRef, serviceProfileRef, direction, loggingRequired.

direction = consumer-to-service \| service-to-consumer \| bidirectional; loggingRequired = true.

<a id="kind_ExternalDomain"></a>

### ExternalDomain

REZ is only a qualified extranet relationship; ENTERPRISE must not automatically receive REZ trust.

Required spec fields: domainType, authorityRef, agreementRef, approvedPrefixPolicyRef, authenticationPolicyRef, validUntil.

domainType = PUBLIC \| REZ\_PARTNER \| ENTERPRISE \| CLOUD\_INTERCONNECT.

<a id="kind_Exposure"></a>

### Exposure

Public ingress requires a PAZ boundary and a distinct authorized application flow downstream.

Required spec fields: wsdRef, exposureType, externalDomainRef, serviceProfileRef, boundaryRef, certificatePolicyRef, dnsPolicyRef, expiresAt, approvalState.

exposureType = publicIngress \| internetEgress \| partner \| enterprise; approvalState = Proposed \| Approved \| Withdrawn.

<a id="kind_EdgeAttachment"></a>

### EdgeAttachment

Provider internal contract; MTU and limits are examples to measure end to end.

Required spec fields: instanceRef, boundaryRef, addressFamilies, transportClass, mtuBytes, routeAuthorityRef, prefixPolicyRef, maximumPrefixes, haProfileRef, sourceIdentityPolicy.

transportClass = precommissioned-overlay \| fabric-routed \| dedicated.

<a id="kind_ZIPRelationship"></a>

### ZIPRelationship

Exactly two endpoints; shared physical edge does not merge relationships. Endpoint kinds checked semantically.

Required spec fields: leftEndpoint, rightEndpoint, pathClass, leftAuthorityRef, rightAuthorityRef, enforcementProfileRef, managementPathRef, defaultAction, heightenedPosturePolicyRef, evidenceProfileRef.

pathClass = data \| management; defaultAction = deny.

<a id="kind_PlatformProfile"></a>

### PlatformProfile

Candidate values deliberately remain unknown. Qualified records require exact versions, evidence, approval, dates and non-empty measured limits.

Required spec fields: product, productVersion, providerSource, providerVersion, apiVersion, networkBackend, capabilities, verifiedLimits, qualificationState, testBundleDigest, evidenceRef, qualifiedAt, revalidateBy, approvalRef, knownLimitations.

qualificationState = Candidate \| Qualified \| Suspended \| Retired.

<a id="kind_WorkloadSecurityDomain"></a>

### WorkloadSecurityDomain

Consumer desired state. Provider placement, actual prefixes, native IDs and status are not request authority.

Required spec fields: tenantRef, categorization, securityProfileRef, assuranceProfileRef, placementProfileRef, availabilityProfileRef, computeProfileRef, storageProfileRefs, backupPolicyRef, evidenceProfileRef, domains, networks, flowRefs, serviceBindingRefs, exposureRefs, lifecycleIntent.

lifecycleIntent = Active \| Retiring.

<a id="kind_SecurityException"></a>

### SecurityException

Approved requires external risk authority; schema cannot prove the authority is genuine.

Required spec fields: requirements, scopeRefs, riskOwnerRef, justification, compensatingControls, approvalRef, validFrom, expiresAt, decision, expiryAction.

decision = Proposed \| Approved \| Rejected \| Revoked \| Closed.

<a id="kind_IncidentOverride"></a>

### IncidentOverride

Containment takes precedence over ordinary reconciliation until authorized release.

Required spec fields: incidentRef, scopeRefs, action, actorRef, authorityRef, effectiveAt, reviewBy, releaseAuthorityRef, state.

action = quarantine \| withdraw-exposure \| suspend-egress \| revoke-binding \| heightened-posture \| freeze-provisioning; state = Proposed \| Active \| Released.

<a id="kind_AuthorizationDecision"></a>

### AuthorizationDecision

Sample explicitly contains no authorization decision.

Required spec fields: scopeRefs, issuedBy, issuedAt, validUntil, decision, conditions, residualRiskRefs, signedArtifactRef.

decision = NotIssued \| Authorized \| Denied \| Revoked.

<a id="kind_EvidenceRecord"></a>

### EvidenceRecord

Sentinel digests and not-run results are illustrations, not assessment artifacts.

Required spec fields: wsdRef, targetGeneration, collectedAt, sourceDigest, policyDigest, profileDigests, testBundleDigest, realizationRefs, tests, technicalConformance, serviceReadiness, authorizationDecisionRef, exceptionRefs, artifactDigest, signatureRef.

technicalConformance = unknown \| compliant \| noncompliant \| exception; serviceReadiness = not-ready \| ready \| degraded \| retired.

<a id="kind_OperationRecord"></a>

### OperationRecord

An operation journal supports partial-apply recovery; it is not a transaction across all providers.

Required spec fields: wsdRef, idempotencyKey, requestedGeneration, planDigest, authorityDomain, stage, completionTokens, compensationPolicyRef, lastError.

authorityDomain = controller \| foundation \| management \| edge \| domain \| workload \| shared-service; stage = received \| admitted \| reserved \| planned \| applying \| verifying \| committed \| compensating \| failed.

<a id="kind_MigrationConnection"></a>

### MigrationConnection

Bounded example; actual source/target zones and protocol require an approved migration design.

Required spec fields: wsdRef, sourceDomainRef, targetDomainRef, flowProfileRef, bandwidthLimitMbps, startsAt, expiresAt, consistencyPolicyRef, cutoverRunbookRef, teardownRequired.

teardownRequired = true.

<a id="kind_RetainedDataRecord"></a>

### RetainedDataRecord

A live service can retire while separately controlled retained data obligations remain.

Required spec fields: formerWsdRef, copyRefs, retentionPolicyRef, holdState, keyPolicyRef, accessAuthorityRef, reviewAt, disposalState.

holdState = none \| active \| released; disposalState = retained \| eligible \| sanitized.

### Reference HTTP surface

These routes define a proposed service API contract, not a deployed endpoint implementation. Authentication, tenant/provider authorization, rate limiting, request-size limits, idempotency and safe error handling apply to every method. Use 400 for invalid syntax, 403 for unauthorized scope, 409 for stale/conflicting state, 422 for unsatisfied semantic/capability requirements, 429 for rate limits and 503 for unavailable mandatory dependencies; do not leak secret or foreign-tenant object details in errors.


<a id="source-table-937"></a>

| Method / route | Semantics |
| --- | --- |
| POST /v1.1/tenants/{tenant}/wsds | Submit versioned desired state; authenticate tenant/service role; require idempotency key; return 202 + operation reference |
| GET /v1.1/tenants/{tenant}/wsds/{name} | Return authorized desired state and redacted observed status; no cross-tenant enumeration |
| PATCH /v1.1/tenants/{tenant}/wsds/{name} | Update desired fields with If-Match/resource version; re-admit security-significant change; server-owned fields denied |
| DELETE /v1.1/tenants/{tenant}/wsds/{name} | Request retirement, not immediate destruction; return operation and remaining finalizers/retention obligations |
| GET /v1.1/operations/{id} | Read only authorized operation journal status and safe error messages; never secrets/raw state |
| GET /v1.1/capabilities | Return entitled service capabilities and limitations; Candidate is not production placement eligibility |
| GET /v1.1/evidence/{id} | Read scoped manifest/artifacts through evidence authorization; log access |
| POST /v1.1/admin/qualification-decisions | Separate provider/security authority publishes reviewed qualification; not consumer write access |
| POST /v1.1/admin/incident-overrides | Scoped authorized containment; independent release authority and reconciliation precedence |

[Previous chapter](62-architecture-acceptance-and-document-release.md) · [Chapter index](README.md) · [Next chapter](71-appendix-b-worked-requests-and-terraform-execution-boundary.md)
