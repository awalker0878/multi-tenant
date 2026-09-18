# 6. Management, services and trust

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/LLD_and_Engineering_Review_Template.docx) · [Chapter index](README.md)

> **Source:** ET — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b25a109f59a09baebb4dfc8c7f5069e9e98421ae5b009dba0e4b08117280511d -->
<!-- SOURCE-BLOCK ET:54 BEGIN -->

<a id="ET_06"></a>

<!-- SOURCE-BLOCK ET:54 END -->

<!-- SOURCE-BLOCK ET:55 BEGIN -->

Actual site values are required. Complete the response fields and identify controlled schedule/diagram references. Unknown or unsupported items remain blocking for their affected scope.

<!-- SOURCE-BLOCK ET:55 END -->

<!-- SOURCE-BLOCK ET:56 BEGIN -->

Baseline and related records: [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [SVC §3](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md#SVC_s_003)

<!-- SOURCE-BLOCK ET:56 END -->

<!-- SOURCE-BLOCK ET:57 BEGIN -->


<a id="source-table-57"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Privilege paths | Actual origin/boundary/target and scoped roles; recovery and supplier access. | {{ET\_PRIVILEGE}} |
| Service endpoints | Actual client, endpoint/protocol, entitlement, return routing and management exclusion. | {{ET\_SERVICES}} |
| DNS/time/telemetry | Authority, required transports, clocks, event identity, buffering, retention and access. | {{ET\_TELEMETRY}} |
| Identity/PKI/KMS | Issuer/role, key-use/admin separation, rotation/revocation and loss behaviour. | {{ET\_TRUST}} |
| Bootstrap transition | Temporary dependencies, owner/expiry and verified transfer to steady state. | {{ET\_BOOTSTRAP}} |
| Dependency loss | Minimum survivors and blocked operations for service/control/key loss. | {{ET\_DEPENDENCY}} |

<!-- SOURCE-BLOCK ET:57 END -->

<!-- SOURCE-BLOCK ET:58 BEGIN -->

<!-- SOURCE-BLOCK ET:58 END -->

<!-- SOURCE-BLOCK ET:59 BEGIN -->

Review disposition: Draft until the actual engineering authority accepts the named scope. A checked form or calculator result does not establish live support, qualification or authorization.

<!-- SOURCE-BLOCK ET:59 END -->

<!-- SOURCE-BLOCK ET:60 BEGIN -->

<!-- SOURCE-BLOCK ET:60 END -->

[Previous chapter](5-compute-storage-and-placement.md) · [Chapter index](README.md) · [Next chapter](7-capacity-mtu-and-failure-calculations.md)
