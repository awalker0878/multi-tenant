# 3. Identity, certificates, keys and independent recovery

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<!-- SOURCE-BLOCK SVC:45 BEGIN -->

<a id="__RefHeading___Toc8879_1525915568"></a>
<a id="SVC_s_003"></a>

<!-- SOURCE-BLOCK SVC:45 END -->

<!-- SOURCE-BLOCK SVC:46 BEGIN -->

Parent architecture: [RA §6](../reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §13](../reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [RA §14](../reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<!-- SOURCE-BLOCK SVC:46 END -->

<!-- SOURCE-BLOCK SVC:47 BEGIN -->

Human operators, provisioning executors, workload identities and recovery custodians have different target scopes and lifetimes. Federation establishes identity, while the target service enforces authorization. Network access remains a separate decision. Record the issuer, role mapping, permitted resource operations, credential/session lifetime, revocation propagation and emergency authority. Avoid reusing an infrastructure administrator credential inside a tenant workload. \[[B2](07-references-parent-basis-and-external-context.md#SVC_src_B2) §§6, 13\]

<!-- SOURCE-BLOCK SVC:47 END -->

<!-- SOURCE-BLOCK SVC:48 BEGIN -->


<a id="source-table-48"></a>

| Trust operation | Reference authority boundary | Failure/recovery question |
| --- | --- | --- |
| Authenticate / issue workload credential | Identity service grants only the requested tenant/service scope. | Can existing tokens persist after revocation, and how is their remaining validity bounded? |
| Issue/renew service certificate | PKI owner validates service identity and controls issuing scope. | Can renewal and trust distribution survive primary management loss? |
| Use encryption key | Service uses the key only for authorized resources and context. | What can run with cached keys, and what cannot restart or attach without KMS? |
| Administer/rotate key | Key administrator controls version/lifecycle separately from ordinary data operations. | Can rotation preserve access to all retained copies and their key versions? |
| Recover keys/trust | Designated custodians use a protected, tested recovery path. | Does recovery require the same encrypted platform that is unavailable? |
| Destroy key | Approved data disposition and proven key/copy scope precede destruction. | Would destruction make a held copy unrecoverable or affect another tenant? |

<!-- SOURCE-BLOCK SVC:48 END -->

<!-- SOURCE-BLOCK SVC:49 BEGIN -->

<!-- SOURCE-BLOCK SVC:49 END -->

<!-- SOURCE-BLOCK SVC:50 BEGIN -->

The cryptographic profile points to the adopted algorithm guidance and secure protocol configuration separately. ITSP.40.111 provides the algorithm context; ITSP.40.062 addresses protocol configuration. A current algorithm name alone does not establish correct TLS, SSH or other protocol settings, endpoint identity validation or a product’s validated operating mode. The selected implementation and approved exceptions remain part of its evidence. \[[S10](07-references-parent-basis-and-external-context.md#SVC_src_S10); [S39](07-references-parent-basis-and-external-context.md#SVC_src_S39)\]

<!-- SOURCE-BLOCK SVC:50 END -->

<!-- SOURCE-BLOCK SVC:51 BEGIN -->

Record the location and administrative control of data keys, infrastructure keys, backup keys, signing keys and trust roots. Those are different roles, not necessarily one product. The architecture does not force key material into Terraform state; reference the approved service and let the authorized execution mechanism obtain only the necessary credential or operation. Unavoidable secret-bearing configuration/state is protected according to its actual sensitivity.

<!-- SOURCE-BLOCK SVC:51 END -->

<!-- SOURCE-BLOCK SVC:52 BEGIN -->


<a id="source-table-52"></a>

| Recovery dependency | Selected reference approach | Required proof |
| --- | --- | --- |
| Identity/PAM outage | Controlled emergency identity with limited target scope and recorded custody. | Normal federation absent; access remains authenticated, auditable and revocable. |
| KMS unavailable | No plaintext or replacement-key fallback; native cache/restart behaviour is declared. | Existing I/O, new boot/attachment and restore outcomes observed. |
| PKI or trust service failure | Preserve approved trust and follow defined renewal/revocation continuity. | Expired/untrusted peer rejected; recovery does not disable validation. |
| Primary management lost | Minimum key/state/catalogue/trust recovery reachable outside the failed dependency. | Recover essential foundations in the approved order and reconcile temporary grants. |

<!-- SOURCE-BLOCK SVC:52 END -->

<!-- SOURCE-BLOCK SVC:53 BEGIN -->

<!-- SOURCE-BLOCK SVC:53 END -->

<!-- SOURCE-BLOCK SVC:54 BEGIN -->

Do not invent cryptoperiods or universal retention durations in this guide. The service/data/security owners select actual values with current source applicability, retained-data obligations and measured recovery feasibility. Independent recovery does not mean unrestricted duplicate administrators; it means a defined, surviving and accountable path.

<!-- SOURCE-BLOCK SVC:54 END -->

<!-- SOURCE-BLOCK SVC:55 BEGIN -->

Related engineering: [Privileged target paths](../../engineering/fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [Parameter and custody decisions](../../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [Bootstrap transfer](../../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)

<!-- SOURCE-BLOCK SVC:55 END -->

[Previous chapter](2-name-time-initialization-and-telemetry-profiles.md) · [Chapter index](README.md) · [Next chapter](4-storage-copies-and-retained-data-ownership.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0009 — Separate management security, platform control and OOB recovery](../../adr/0009-separate-management-security-platform-control-and-oob-recovery.md)
- [ADR-0029 — Keep recovery trust material independent of the platform it unlocks](../../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)

<!-- END GENERATED DECISION LINKS -->
