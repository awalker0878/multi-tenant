# 13. Identity, cryptography and service trust

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3664_865363315"></a>
<a id="RA_s_013"></a>

Identity is enforced at every administrative and data-service interface, not inferred from network location. Human administrators, automation executors, workload identities and recovery identities have separate roles and credential lifecycles. A tenant’s ability to use a service does not grant authority over its configuration, keys or other tenants’ data.

Federated identity supplies authoritative user/group membership where supported. Privileged access is task-scoped through the approved management path, with strong authentication, controlled duration and auditable approval. Machine credentials are restricted to the APIs and resources required by their provisioning package. Where short-lived credentials are unavailable, vaulted static credentials need bounded privilege, rotation, revocation and monitoring; that limitation is visible in the platform design.


<a id="source-table-201"></a>

| Trust service | Required architectural decision | Failure expectation |
| --- | --- | --- |
| Identity/PAM | Issuer, role mapping, privileged path, token/session lifetime and emergency authority | New privileged activity stops or uses the explicitly controlled emergency path |
| PKI | Trust roots, issuing scope, endpoint identity, renewal and revocation | No disabled certificate validation as a recovery shortcut |
| KMS/HSM | Key-use versus administration, tenant/provider scope, recovery custody and location | No plaintext or replacement-key fallback; cached-key behaviour is documented |
| Artifact signing | Who builds, approves, signs and publishes platform images and modules | Untrusted or revoked artifacts are not promoted into privileged execution |
| Evidence protection | Who can write, read, retain or dispose of operational evidence | Collection loss is visible and follows the agreed safe-state policy |

The cryptographic architecture separates key use, key administration, key recovery and destruction. It identifies whether keys are tenant-controlled, provider-controlled or shared-service controlled, and what access administrators can exercise. Data replicas, backups, logs and diagnostics are included in the location and custody model. Residency alone does not establish control over administrative access or legal obligations; approved constraints come from the responsible authorities.

Use a versioned cryptographic profile rather than a permanent algorithm shortcut in the architecture. The current ITSP.40.111 reference includes version 5 and its effective date; implementation must select approved algorithms, operating modes and applicable validated modules for its exact environment. Maintain a crypto inventory and transition dependencies without claiming that every vendor feature already meets them. \[[S10](34-appendix-d-sources-and-review-status.md#RA_src_S10)\]

Key and identity recovery must avoid circular dependencies. The sole means of unlocking a failed storage platform cannot exist only on that encrypted platform. The recovery design provides controlled access to the minimum independent trust material and tests it during a management/platform outage. Retained data must not lose its only usable key because the associated live workload was deleted.

Terraform plans, state and logs receive the same information-handling care as other privileged infrastructure records. Display redaction is not proof that secrets are absent from stored state. Short-lived credentials and supported secret-avoidance mechanisms reduce exposure, but backend access control, encryption, retention and recovery remain necessary. The architecture assigns these controls to the provisioning service rather than exposing them to every tenant operator.

Algorithm selection and secure protocol configuration are complementary decisions. Use the adopted ITSP.40.111 algorithm profile together with applicable protocol guidance such as ITSP.40.062; record endpoint identity, trust, required configuration and implementation evidence separately from product feature labels. SVC §3 develops the custody and recovery dependencies. \[[S10](34-appendix-d-sources-and-review-status.md#RA_src_S10); [S39](34-appendix-d-sources-and-review-status.md#RA_src_S39)\]

Related engineering: [SVC §3 — Identity, certificates, keys and independent recovery](../shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)

[Previous chapter](12-storage-backup-and-data-isolation-architecture.md) · [Chapter index](README.md) · [Next chapter](14-availability-multi-site-operation-and-recovery-topology.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0029 — Keep recovery trust material independent of the platform it unlocks](../../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<!-- END GENERATED DECISION LINKS -->
