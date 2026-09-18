# Appendix A — Canonical object contract and API surface

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:804 BEGIN -->

<a id="__RefHeading___Toc13423_1645000677"></a>
<a id="app_A"></a>

<!-- SOURCE-BLOCK HB11:804 END -->

<!-- SOURCE-BLOCK HB11:805 BEGIN -->

The companion schemas are the exact machine-readable reference for field types, closed property sets, enums and conditional structural requirements. The following dictionary lists every object and every required spec field. References have kind, name and immutable semantic version. Objects use apiVersion: hosting.platform/v1.1, kind, metadata and spec; status is a separately authorized observed-state surface. \[[S30](77-appendix-h-primary-sources-and-implementation-references.md#S30)\]

<!-- SOURCE-BLOCK HB11:805 END -->

<!-- SOURCE-BLOCK HB11:806 BEGIN -->


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

<!-- SOURCE-BLOCK HB11:806 END -->

<!-- SOURCE-BLOCK HB11:807 BEGIN -->

<a id="__RefHeading___Toc13425_1645000677"></a>

## Object definitions

<!-- SOURCE-BLOCK HB11:807 END -->

<!-- SOURCE-BLOCK HB11:808 BEGIN -->

<a id="kind_TenantNamespace"></a>

### TenantNamespace

<!-- SOURCE-BLOCK HB11:808 END -->

<!-- SOURCE-BLOCK HB11:809 BEGIN -->

Administrative scope. Quotas are illustrative entitlements, not measured available capacity.

<!-- SOURCE-BLOCK HB11:809 END -->

<!-- SOURCE-BLOCK HB11:810 BEGIN -->

Required spec fields: identityGroups, entitlements, quotas, lifecycle, securityAuthorityRef.

<!-- SOURCE-BLOCK HB11:810 END -->

<!-- SOURCE-BLOCK HB11:811 BEGIN -->

lifecycle = Requested \| Active \| Restricted \| Suspended \| Retiring \| Retired.

<!-- SOURCE-BLOCK HB11:811 END -->

<!-- SOURCE-BLOCK HB11:812 BEGIN -->

<a id="kind_SecurityProfile"></a>

### SecurityProfile

<!-- SOURCE-BLOCK HB11:812 END -->

<!-- SOURCE-BLOCK HB11:813 BEGIN -->

Impact levels and tailored control selection are separate from operational uptime. Empty control selection is legal only as a non-approved design example.

<!-- SOURCE-BLOCK HB11:813 END -->

<!-- SOURCE-BLOCK HB11:814 BEGIN -->

Required spec fields: confidentiality, integrity, availabilityImpact, catalogueEdition, controlSelections, mandatoryServiceProfiles, cryptographicProfileRef, evidenceProfileRef, approvalState.

<!-- SOURCE-BLOCK HB11:814 END -->

<!-- SOURCE-BLOCK HB11:815 BEGIN -->

confidentiality = Unclassified \| ProtectedA \| ProtectedB; integrity = Low \| Medium \| High; availabilityImpact = Low \| Medium \| High; approvalState = Proposed \| Approved \| Retired.

<!-- SOURCE-BLOCK HB11:815 END -->

<!-- SOURCE-BLOCK HB11:816 BEGIN -->

<a id="kind_AssuranceProfile"></a>

### AssuranceProfile

<!-- SOURCE-BLOCK HB11:816 END -->

<!-- SOURCE-BLOCK HB11:817 BEGIN -->

Dedicated scope is a vector; numeric values are local proposed examples.

<!-- SOURCE-BLOCK HB11:817 END -->

<!-- SOURCE-BLOCK HB11:818 BEGIN -->

Required spec fields: level, isolation, hostZoneSharing, requiredTests, maxEvidenceAgeHours, approvalState.

<!-- SOURCE-BLOCK HB11:818 END -->

<!-- SOURCE-BLOCK HB11:819 BEGIN -->

level = Standard \| Enhanced \| Dedicated; hostZoneSharing = single-zone \| approved-alternative; approvalState = Proposed \| Approved \| Retired.

<!-- SOURCE-BLOCK HB11:819 END -->

<!-- SOURCE-BLOCK HB11:820 BEGIN -->

<a id="kind_AvailabilityProfile"></a>

### AvailabilityProfile

<!-- SOURCE-BLOCK HB11:820 END -->

<!-- SOURCE-BLOCK HB11:821 BEGIN -->

Measured service SLO, not the availability-impact classification and not a delivered guarantee.

<!-- SOURCE-BLOCK HB11:821 END -->

<!-- SOURCE-BLOCK HB11:822 BEGIN -->

Required spec fields: sloPercent, measurementWindowDays, minimumFailureDomains, coveredFailureModel, maintenancePolicy, recoveryProfileRef, approvalState.

<!-- SOURCE-BLOCK HB11:822 END -->

<!-- SOURCE-BLOCK HB11:823 BEGIN -->

approvalState = Proposed \| Approved \| Retired.

<!-- SOURCE-BLOCK HB11:823 END -->

<!-- SOURCE-BLOCK HB11:824 BEGIN -->

<a id="kind_RecoveryProfile"></a>

### RecoveryProfile

<!-- SOURCE-BLOCK HB11:824 END -->

<!-- SOURCE-BLOCK HB11:825 BEGIN -->

RTO/RPO include the service-specific measurement boundary.

<!-- SOURCE-BLOCK HB11:825 END -->

<!-- SOURCE-BLOCK HB11:826 BEGIN -->

Required spec fields: rtoMinutes, rpoMinutes, exerciseIntervalDays, recoverySitePolicy, fencingRequired, bootstrapRunbookRef, failbackRunbookRef.

<!-- SOURCE-BLOCK HB11:826 END -->

<!-- SOURCE-BLOCK HB11:827 BEGIN -->

fencingRequired = true.

<!-- SOURCE-BLOCK HB11:827 END -->

<!-- SOURCE-BLOCK HB11:828 BEGIN -->

<a id="kind_BackupPolicy"></a>

### BackupPolicy

<!-- SOURCE-BLOCK HB11:828 END -->

<!-- SOURCE-BLOCK HB11:829 BEGIN -->

Retention is a proposed example. Successful restore is a mandatory acceptance outcome.

<!-- SOURCE-BLOCK HB11:829 END -->

<!-- SOURCE-BLOCK HB11:830 BEGIN -->

Required spec fields: retentionDays, immutableCopyRequired, isolatedAdministrationRequired, copyLocationPolicy, restoreTestIntervalDays, keyPolicyRef, holdOverridesDeletion.

<!-- SOURCE-BLOCK HB11:830 END -->

<!-- SOURCE-BLOCK HB11:831 BEGIN -->

isolatedAdministrationRequired = true; holdOverridesDeletion = true.

<!-- SOURCE-BLOCK HB11:831 END -->

<!-- SOURCE-BLOCK HB11:832 BEGIN -->

<a id="kind_CryptographicProfile"></a>

### CryptographicProfile

<!-- SOURCE-BLOCK HB11:832 END -->

<!-- SOURCE-BLOCK HB11:833 BEGIN -->

Algorithms are selected through an approved external policy; this sample does not invent a certification.

<!-- SOURCE-BLOCK HB11:833 END -->

<!-- SOURCE-BLOCK HB11:834 BEGIN -->

Required spec fields: guidanceEdition, transportPolicyRef, atRestRequired, moduleValidationPolicy, algorithmInventoryRef, keyPolicyRef, plaintextFallbackAllowed.

<!-- SOURCE-BLOCK HB11:834 END -->

<!-- SOURCE-BLOCK HB11:835 BEGIN -->

plaintextFallbackAllowed = false.

<!-- SOURCE-BLOCK HB11:835 END -->

<!-- SOURCE-BLOCK HB11:836 BEGIN -->

<a id="kind_KeyPolicy"></a>

### KeyPolicy

<!-- SOURCE-BLOCK HB11:836 END -->

<!-- SOURCE-BLOCK HB11:837 BEGIN -->

Rotation intervals need local approval; destroy only keys with proven exclusive eligible scope.

<!-- SOURCE-BLOCK HB11:837 END -->

<!-- SOURCE-BLOCK HB11:838 BEGIN -->

Required spec fields: ownerRef, custodyPolicy, kmsServiceProfileRef, rotationIntervalDays, recoveryPolicyRef, destructionApprovalRef, sharedKeyDestructionAllowed.

<!-- SOURCE-BLOCK HB11:838 END -->

<!-- SOURCE-BLOCK HB11:839 BEGIN -->

sharedKeyDestructionAllowed = false.

<!-- SOURCE-BLOCK HB11:839 END -->

<!-- SOURCE-BLOCK HB11:840 BEGIN -->

<a id="kind_ComputeProfile"></a>

### ComputeProfile

<!-- SOURCE-BLOCK HB11:840 END -->

<!-- SOURCE-BLOCK HB11:841 BEGIN -->

Compute requirements are independent of vendor VM identifiers.

<!-- SOURCE-BLOCK HB11:841 END -->

<!-- SOURCE-BLOCK HB11:842 BEGIN -->

Required spec fields: cpuArchitecture, minimumMemoryGiB, minimumVcpus, hostZoneSharing, secureBootPolicy, overcommitPolicy, imageProfileRef, antiAffinityRequired.

<!-- SOURCE-BLOCK HB11:842 END -->

<!-- SOURCE-BLOCK HB11:843 BEGIN -->

cpuArchitecture = x86\_64 \| aarch64; hostZoneSharing = single-zone \| approved-alternative.

<!-- SOURCE-BLOCK HB11:843 END -->

<!-- SOURCE-BLOCK HB11:844 BEGIN -->

<a id="kind_StorageProfile"></a>

### StorageProfile

<!-- SOURCE-BLOCK HB11:844 END -->

<!-- SOURCE-BLOCK HB11:845 BEGIN -->

Block, file and object profiles cannot be treated as interchangeable just because all store bytes.

<!-- SOURCE-BLOCK HB11:845 END -->

<!-- SOURCE-BLOCK HB11:846 BEGIN -->

Required spec fields: interface, minimumCapacityGiB, performanceClass, isolationPolicy, cryptographicProfileRef, backupPolicyRef, copyLineageRequired, exportFormatPolicy.

<!-- SOURCE-BLOCK HB11:846 END -->

<!-- SOURCE-BLOCK HB11:847 BEGIN -->

interface = block \| file \| object; copyLineageRequired = true.

<!-- SOURCE-BLOCK HB11:847 END -->

<!-- SOURCE-BLOCK HB11:848 BEGIN -->

<a id="kind_ImageProfile"></a>

### ImageProfile

<!-- SOURCE-BLOCK HB11:848 END -->

<!-- SOURCE-BLOCK HB11:849 BEGIN -->

Illustrative unapproved image. Zero digest is a sentinel, not a production artifact digest.

<!-- SOURCE-BLOCK HB11:849 END -->

<!-- SOURCE-BLOCK HB11:850 BEGIN -->

Required spec fields: artifactRef, artifactDigest, provenanceRef, baselineRef, vulnerabilityDispositionRef, retirementAt, approved.

<!-- SOURCE-BLOCK HB11:850 END -->

<!-- SOURCE-BLOCK HB11:851 BEGIN -->

<a id="kind_PlacementProfile"></a>

### PlacementProfile

<!-- SOURCE-BLOCK HB11:851 END -->

<!-- SOURCE-BLOCK HB11:852 BEGIN -->

Location and support constraints are independent facts; residency does not establish sovereignty.

<!-- SOURCE-BLOCK HB11:852 END -->

<!-- SOURCE-BLOCK HB11:853 BEGIN -->

Required spec fields: allowedSites, allowedPlatforms, dataLocations, controlLocations, supportAccessPolicy, keyCustodyPolicy, coResidencyPolicyRef, portabilityExtensions.

<!-- SOURCE-BLOCK HB11:853 END -->

<!-- SOURCE-BLOCK HB11:854 BEGIN -->

<a id="kind_EvidenceProfile"></a>

### EvidenceProfile

<!-- SOURCE-BLOCK HB11:854 END -->

<!-- SOURCE-BLOCK HB11:855 BEGIN -->

Evidence freshness follows change and profile scope, not simply a single timer.

<!-- SOURCE-BLOCK HB11:855 END -->

<!-- SOURCE-BLOCK HB11:856 BEGIN -->

Required spec fields: requiredTests, maxAgeHours, retentionDays, integrityPolicy, accessPolicy.

<!-- SOURCE-BLOCK HB11:856 END -->

<!-- SOURCE-BLOCK HB11:857 BEGIN -->

<a id="kind_FlowProfile"></a>

### FlowProfile

<!-- SOURCE-BLOCK HB11:857 END -->

<!-- SOURCE-BLOCK HB11:858 BEGIN -->

Raw firewall rule order and provider identifiers stay out of the consumer contract.

<!-- SOURCE-BLOCK HB11:858 END -->

<!-- SOURCE-BLOCK HB11:859 BEGIN -->

Required spec fields: protocol, ports, stateful, tlsRequired, mtlsRequired, l7PolicyRef, loggingProfileRef.

<!-- SOURCE-BLOCK HB11:859 END -->

<!-- SOURCE-BLOCK HB11:860 BEGIN -->

protocol = tcp \| udp \| icmp \| icmpv6 \| other.

<!-- SOURCE-BLOCK HB11:860 END -->

<!-- SOURCE-BLOCK HB11:861 BEGIN -->

<a id="kind_ServiceProfile"></a>

### ServiceProfile

<!-- SOURCE-BLOCK HB11:861 END -->

<!-- SOURCE-BLOCK HB11:862 BEGIN -->

Service endpoints are explicit; binding does not grant a shared subnet or management path.

<!-- SOURCE-BLOCK HB11:862 END -->

<!-- SOURCE-BLOCK HB11:863 BEGIN -->

Required spec fields: serviceType, flowProfileRef, endpointNames, providerScope, availabilityProfileRef, managementEndpointExposed.

<!-- SOURCE-BLOCK HB11:863 END -->

<!-- SOURCE-BLOCK HB11:864 BEGIN -->

serviceType = dns \| time \| identity \| logging \| backup \| kms \| pki \| monitoring \| other; managementEndpointExposed = false.

<!-- SOURCE-BLOCK HB11:864 END -->

<!-- SOURCE-BLOCK HB11:865 BEGIN -->

<a id="kind_SecurityDomain"></a>

### SecurityDomain

<!-- SOURCE-BLOCK HB11:865 END -->

<!-- SOURCE-BLOCK HB11:866 BEGIN -->

Logical authority, independent of site-specific native routing contexts. MZ is provider-only.

<!-- SOURCE-BLOCK HB11:866 END -->

<!-- SOURCE-BLOCK HB11:867 BEGIN -->

Required spec fields: zoneClass, authorityRef, tenantScope, assuranceProfileRef, sharingPolicy, addressPolicyRef.

<!-- SOURCE-BLOCK HB11:867 END -->

<!-- SOURCE-BLOCK HB11:868 BEGIN -->

zoneClass = PAZ \| OZ \| RZ \| HRZ \| MZ; sharingPolicy = exclusive-wsd \| same-authority-approved \| provider-service.

<!-- SOURCE-BLOCK HB11:868 END -->

<!-- SOURCE-BLOCK HB11:869 BEGIN -->

<a id="kind_SecurityDomainInstance"></a>

### SecurityDomainInstance

<!-- SOURCE-BLOCK HB11:869 END -->

<!-- SOURCE-BLOCK HB11:870 BEGIN -->

Provider-internal realization; a candidate platform cannot become Ready by passing schema validation.

<!-- SOURCE-BLOCK HB11:870 END -->

<!-- SOURCE-BLOCK HB11:871 BEGIN -->

Required spec fields: domainRef, siteRef, platformProfileRef, addressScopeRef, edgeAttachmentRefs, failureDomainRef.

<!-- SOURCE-BLOCK HB11:871 END -->

<!-- SOURCE-BLOCK HB11:872 BEGIN -->

<a id="kind_Network"></a>

### Network

<!-- SOURCE-BLOCK HB11:872 END -->

<!-- SOURCE-BLOCK HB11:873 BEGIN -->

Observed provider network; example prefixes are not allocations for a real environment.

<!-- SOURCE-BLOCK HB11:873 END -->

<!-- SOURCE-BLOCK HB11:874 BEGIN -->

Required spec fields: wsdRef, instanceRef, ipv4Prefix, ipv6Prefix, allocationRef, dhcpProfileRef, dnsPolicyRef, endpointSecurityPolicyRef.

<!-- SOURCE-BLOCK HB11:874 END -->

<!-- SOURCE-BLOCK HB11:875 BEGIN -->

<a id="kind_FlowIntent"></a>

### FlowIntent

<!-- SOURCE-BLOCK HB11:875 END -->

<!-- SOURCE-BLOCK HB11:876 BEGIN -->

Flow approval and path compilation are semantic operations, not inferred from this JSON alone.

<!-- SOURCE-BLOCK HB11:876 END -->

<!-- SOURCE-BLOCK HB11:877 BEGIN -->

Required spec fields: wsdRef, source, destination, flowProfileRef, direction, justification, validFrom, expiresAt, loggingRequired.

<!-- SOURCE-BLOCK HB11:877 END -->

<!-- SOURCE-BLOCK HB11:878 BEGIN -->

direction = source-to-destination \| bidirectional; loggingRequired = true.

<!-- SOURCE-BLOCK HB11:878 END -->

<!-- SOURCE-BLOCK HB11:879 BEGIN -->

<a id="kind_ServiceBinding"></a>

### ServiceBinding

<!-- SOURCE-BLOCK HB11:879 END -->

<!-- SOURCE-BLOCK HB11:880 BEGIN -->

Publishing a service and authorizing a consumer binding are separate decisions.

<!-- SOURCE-BLOCK HB11:880 END -->

<!-- SOURCE-BLOCK HB11:881 BEGIN -->

Required spec fields: wsdRef, consumerDomainRef, serviceProfileRef, direction, loggingRequired.

<!-- SOURCE-BLOCK HB11:881 END -->

<!-- SOURCE-BLOCK HB11:882 BEGIN -->

direction = consumer-to-service \| service-to-consumer \| bidirectional; loggingRequired = true.

<!-- SOURCE-BLOCK HB11:882 END -->

<!-- SOURCE-BLOCK HB11:883 BEGIN -->

<a id="kind_ExternalDomain"></a>

### ExternalDomain

<!-- SOURCE-BLOCK HB11:883 END -->

<!-- SOURCE-BLOCK HB11:884 BEGIN -->

REZ is only a qualified extranet relationship; ENTERPRISE must not automatically receive REZ trust.

<!-- SOURCE-BLOCK HB11:884 END -->

<!-- SOURCE-BLOCK HB11:885 BEGIN -->

Required spec fields: domainType, authorityRef, agreementRef, approvedPrefixPolicyRef, authenticationPolicyRef, validUntil.

<!-- SOURCE-BLOCK HB11:885 END -->

<!-- SOURCE-BLOCK HB11:886 BEGIN -->

domainType = PUBLIC \| REZ\_PARTNER \| ENTERPRISE \| CLOUD\_INTERCONNECT.

<!-- SOURCE-BLOCK HB11:886 END -->

<!-- SOURCE-BLOCK HB11:887 BEGIN -->

<a id="kind_Exposure"></a>

### Exposure

<!-- SOURCE-BLOCK HB11:887 END -->

<!-- SOURCE-BLOCK HB11:888 BEGIN -->

Public ingress requires a PAZ boundary and a distinct authorized application flow downstream.

<!-- SOURCE-BLOCK HB11:888 END -->

<!-- SOURCE-BLOCK HB11:889 BEGIN -->

Required spec fields: wsdRef, exposureType, externalDomainRef, serviceProfileRef, boundaryRef, certificatePolicyRef, dnsPolicyRef, expiresAt, approvalState.

<!-- SOURCE-BLOCK HB11:889 END -->

<!-- SOURCE-BLOCK HB11:890 BEGIN -->

exposureType = publicIngress \| internetEgress \| partner \| enterprise; approvalState = Proposed \| Approved \| Withdrawn.

<!-- SOURCE-BLOCK HB11:890 END -->

<!-- SOURCE-BLOCK HB11:891 BEGIN -->

<a id="kind_EdgeAttachment"></a>

### EdgeAttachment

<!-- SOURCE-BLOCK HB11:891 END -->

<!-- SOURCE-BLOCK HB11:892 BEGIN -->

Provider internal contract; MTU and limits are examples to measure end to end.

<!-- SOURCE-BLOCK HB11:892 END -->

<!-- SOURCE-BLOCK HB11:893 BEGIN -->

Required spec fields: instanceRef, boundaryRef, addressFamilies, transportClass, mtuBytes, routeAuthorityRef, prefixPolicyRef, maximumPrefixes, haProfileRef, sourceIdentityPolicy.

<!-- SOURCE-BLOCK HB11:893 END -->

<!-- SOURCE-BLOCK HB11:894 BEGIN -->

transportClass = precommissioned-overlay \| fabric-routed \| dedicated.

<!-- SOURCE-BLOCK HB11:894 END -->

<!-- SOURCE-BLOCK HB11:895 BEGIN -->

<a id="kind_ZIPRelationship"></a>

### ZIPRelationship

<!-- SOURCE-BLOCK HB11:895 END -->

<!-- SOURCE-BLOCK HB11:896 BEGIN -->

Exactly two endpoints; shared physical edge does not merge relationships. Endpoint kinds checked semantically.

<!-- SOURCE-BLOCK HB11:896 END -->

<!-- SOURCE-BLOCK HB11:897 BEGIN -->

Required spec fields: leftEndpoint, rightEndpoint, pathClass, leftAuthorityRef, rightAuthorityRef, enforcementProfileRef, managementPathRef, defaultAction, heightenedPosturePolicyRef, evidenceProfileRef.

<!-- SOURCE-BLOCK HB11:897 END -->

<!-- SOURCE-BLOCK HB11:898 BEGIN -->

pathClass = data \| management; defaultAction = deny.

<!-- SOURCE-BLOCK HB11:898 END -->

<!-- SOURCE-BLOCK HB11:899 BEGIN -->

<a id="kind_PlatformProfile"></a>

### PlatformProfile

<!-- SOURCE-BLOCK HB11:899 END -->

<!-- SOURCE-BLOCK HB11:900 BEGIN -->

Candidate values deliberately remain unknown. Qualified records require exact versions, evidence, approval, dates and non-empty measured limits.

<!-- SOURCE-BLOCK HB11:900 END -->

<!-- SOURCE-BLOCK HB11:901 BEGIN -->

Required spec fields: product, productVersion, providerSource, providerVersion, apiVersion, networkBackend, capabilities, verifiedLimits, qualificationState, testBundleDigest, evidenceRef, qualifiedAt, revalidateBy, approvalRef, knownLimitations.

<!-- SOURCE-BLOCK HB11:901 END -->

<!-- SOURCE-BLOCK HB11:902 BEGIN -->

qualificationState = Candidate \| Qualified \| Suspended \| Retired.

<!-- SOURCE-BLOCK HB11:902 END -->

<!-- SOURCE-BLOCK HB11:903 BEGIN -->

<a id="kind_WorkloadSecurityDomain"></a>

### WorkloadSecurityDomain

<!-- SOURCE-BLOCK HB11:903 END -->

<!-- SOURCE-BLOCK HB11:904 BEGIN -->

Consumer desired state. Provider placement, actual prefixes, native IDs and status are not request authority.

<!-- SOURCE-BLOCK HB11:904 END -->

<!-- SOURCE-BLOCK HB11:905 BEGIN -->

Required spec fields: tenantRef, categorization, securityProfileRef, assuranceProfileRef, placementProfileRef, availabilityProfileRef, computeProfileRef, storageProfileRefs, backupPolicyRef, evidenceProfileRef, domains, networks, flowRefs, serviceBindingRefs, exposureRefs, lifecycleIntent.

<!-- SOURCE-BLOCK HB11:905 END -->

<!-- SOURCE-BLOCK HB11:906 BEGIN -->

lifecycleIntent = Active \| Retiring.

<!-- SOURCE-BLOCK HB11:906 END -->

<!-- SOURCE-BLOCK HB11:907 BEGIN -->

<a id="kind_SecurityException"></a>

### SecurityException

<!-- SOURCE-BLOCK HB11:907 END -->

<!-- SOURCE-BLOCK HB11:908 BEGIN -->

Approved requires external risk authority; schema cannot prove the authority is genuine.

<!-- SOURCE-BLOCK HB11:908 END -->

<!-- SOURCE-BLOCK HB11:909 BEGIN -->

Required spec fields: requirements, scopeRefs, riskOwnerRef, justification, compensatingControls, approvalRef, validFrom, expiresAt, decision, expiryAction.

<!-- SOURCE-BLOCK HB11:909 END -->

<!-- SOURCE-BLOCK HB11:910 BEGIN -->

decision = Proposed \| Approved \| Rejected \| Revoked \| Closed.

<!-- SOURCE-BLOCK HB11:910 END -->

<!-- SOURCE-BLOCK HB11:911 BEGIN -->

<a id="kind_IncidentOverride"></a>

### IncidentOverride

<!-- SOURCE-BLOCK HB11:911 END -->

<!-- SOURCE-BLOCK HB11:912 BEGIN -->

Containment takes precedence over ordinary reconciliation until authorized release.

<!-- SOURCE-BLOCK HB11:912 END -->

<!-- SOURCE-BLOCK HB11:913 BEGIN -->

Required spec fields: incidentRef, scopeRefs, action, actorRef, authorityRef, effectiveAt, reviewBy, releaseAuthorityRef, state.

<!-- SOURCE-BLOCK HB11:913 END -->

<!-- SOURCE-BLOCK HB11:914 BEGIN -->

action = quarantine \| withdraw-exposure \| suspend-egress \| revoke-binding \| heightened-posture \| freeze-provisioning; state = Proposed \| Active \| Released.

<!-- SOURCE-BLOCK HB11:914 END -->

<!-- SOURCE-BLOCK HB11:915 BEGIN -->

<a id="kind_AuthorizationDecision"></a>

### AuthorizationDecision

<!-- SOURCE-BLOCK HB11:915 END -->

<!-- SOURCE-BLOCK HB11:916 BEGIN -->

Sample explicitly contains no authorization decision.

<!-- SOURCE-BLOCK HB11:916 END -->

<!-- SOURCE-BLOCK HB11:917 BEGIN -->

Required spec fields: scopeRefs, issuedBy, issuedAt, validUntil, decision, conditions, residualRiskRefs, signedArtifactRef.

<!-- SOURCE-BLOCK HB11:917 END -->

<!-- SOURCE-BLOCK HB11:918 BEGIN -->

decision = NotIssued \| Authorized \| Denied \| Revoked.

<!-- SOURCE-BLOCK HB11:918 END -->

<!-- SOURCE-BLOCK HB11:919 BEGIN -->

<a id="kind_EvidenceRecord"></a>

### EvidenceRecord

<!-- SOURCE-BLOCK HB11:919 END -->

<!-- SOURCE-BLOCK HB11:920 BEGIN -->

Sentinel digests and not-run results are illustrations, not assessment artifacts.

<!-- SOURCE-BLOCK HB11:920 END -->

<!-- SOURCE-BLOCK HB11:921 BEGIN -->

Required spec fields: wsdRef, targetGeneration, collectedAt, sourceDigest, policyDigest, profileDigests, testBundleDigest, realizationRefs, tests, technicalConformance, serviceReadiness, authorizationDecisionRef, exceptionRefs, artifactDigest, signatureRef.

<!-- SOURCE-BLOCK HB11:921 END -->

<!-- SOURCE-BLOCK HB11:922 BEGIN -->

technicalConformance = unknown \| compliant \| noncompliant \| exception; serviceReadiness = not-ready \| ready \| degraded \| retired.

<!-- SOURCE-BLOCK HB11:922 END -->

<!-- SOURCE-BLOCK HB11:923 BEGIN -->

<a id="kind_OperationRecord"></a>

### OperationRecord

<!-- SOURCE-BLOCK HB11:923 END -->

<!-- SOURCE-BLOCK HB11:924 BEGIN -->

An operation journal supports partial-apply recovery; it is not a transaction across all providers.

<!-- SOURCE-BLOCK HB11:924 END -->

<!-- SOURCE-BLOCK HB11:925 BEGIN -->

Required spec fields: wsdRef, idempotencyKey, requestedGeneration, planDigest, authorityDomain, stage, completionTokens, compensationPolicyRef, lastError.

<!-- SOURCE-BLOCK HB11:925 END -->

<!-- SOURCE-BLOCK HB11:926 BEGIN -->

authorityDomain = controller \| foundation \| management \| edge \| domain \| workload \| shared-service; stage = received \| admitted \| reserved \| planned \| applying \| verifying \| committed \| compensating \| failed.

<!-- SOURCE-BLOCK HB11:926 END -->

<!-- SOURCE-BLOCK HB11:927 BEGIN -->

<a id="kind_MigrationConnection"></a>

### MigrationConnection

<!-- SOURCE-BLOCK HB11:927 END -->

<!-- SOURCE-BLOCK HB11:928 BEGIN -->

Bounded example; actual source/target zones and protocol require an approved migration design.

<!-- SOURCE-BLOCK HB11:928 END -->

<!-- SOURCE-BLOCK HB11:929 BEGIN -->

Required spec fields: wsdRef, sourceDomainRef, targetDomainRef, flowProfileRef, bandwidthLimitMbps, startsAt, expiresAt, consistencyPolicyRef, cutoverRunbookRef, teardownRequired.

<!-- SOURCE-BLOCK HB11:929 END -->

<!-- SOURCE-BLOCK HB11:930 BEGIN -->

teardownRequired = true.

<!-- SOURCE-BLOCK HB11:930 END -->

<!-- SOURCE-BLOCK HB11:931 BEGIN -->

<a id="kind_RetainedDataRecord"></a>

### RetainedDataRecord

<!-- SOURCE-BLOCK HB11:931 END -->

<!-- SOURCE-BLOCK HB11:932 BEGIN -->

A live service can retire while separately controlled retained data obligations remain.

<!-- SOURCE-BLOCK HB11:932 END -->

<!-- SOURCE-BLOCK HB11:933 BEGIN -->

Required spec fields: formerWsdRef, copyRefs, retentionPolicyRef, holdState, keyPolicyRef, accessAuthorityRef, reviewAt, disposalState.

<!-- SOURCE-BLOCK HB11:933 END -->

<!-- SOURCE-BLOCK HB11:934 BEGIN -->

holdState = none \| active \| released; disposalState = retained \| eligible \| sanitized.

<!-- SOURCE-BLOCK HB11:934 END -->

<!-- SOURCE-BLOCK HB11:935 BEGIN -->

### Reference HTTP surface

<!-- SOURCE-BLOCK HB11:935 END -->

<!-- SOURCE-BLOCK HB11:936 BEGIN -->

These routes define a proposed service API contract, not a deployed endpoint implementation. Authentication, tenant/provider authorization, rate limiting, request-size limits, idempotency and safe error handling apply to every method. Use 400 for invalid syntax, 403 for unauthorized scope, 409 for stale/conflicting state, 422 for unsatisfied semantic/capability requirements, 429 for rate limits and 503 for unavailable mandatory dependencies; do not leak secret or foreign-tenant object details in errors.

<!-- SOURCE-BLOCK HB11:936 END -->

<!-- SOURCE-BLOCK HB11:937 BEGIN -->


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

<!-- SOURCE-BLOCK HB11:937 END -->

[Previous chapter](62-architecture-acceptance-and-document-release.md) · [Chapter index](README.md) · [Next chapter](71-appendix-b-worked-requests-and-terraform-execution-boundary.md)
