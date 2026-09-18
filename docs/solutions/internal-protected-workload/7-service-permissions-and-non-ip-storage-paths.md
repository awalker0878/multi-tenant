# 7. Service permissions and non-IP storage paths

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S07"></a>

The permissions are proposed test-service selections. They are not a blanket firewall configuration. DNS recursion, authoritative changes, time service, logging administration, repository publication and protection management each have their own authority. Only the consumption operations explicitly selected here are part of the tenant path.

DNS over TCP and UDP is tested, including truncated-response fallback. RFC 7766 provides the general-purpose DNS TCP requirement. \[R14-04\] Log ingestion uses the selected authenticated collector protocol; the example does not guess a product-specific port or substitute ingestion permission for search or administrative rights.

Virtual-disk encryption does not imply that a guest needs a KMS network binding. The hypervisor/storage service may be the key-service client. Likewise, backup orchestration may use protected platform APIs while data moves through a different supported interface. Those management and data paths must be designed separately, rather than adding them to the guest permit list.

Required provider-initiated health checks or collection must identify the exact source, destination, operation and reason. Stateful response permission is not permission to initiate a new reverse session. Unapproved extra NICs, address-pair changes, native routers and service-host forwarding remain excluded.


<a id="source-table-84"></a>

| Flow / origin | Destination and operation | Required denial or separate authority |
| --- | --- | --- |
| F14-01 / processor-01 | data-01, TCP/443, endpoint TLS validation | New reverse initiation and other tenant data endpoints denied. |
| F14-02 / processor-02 | data-02, TCP/443, same service semantics | Policy is independent of F14-01. |
| F14-03 / entitled tenant endpoints | Approved resolver .138, UDP/53 and TCP/53 | Other resolvers, zone administration and general provider subnet access denied. |
| F14-04 / entitled time clients | Approved time endpoint .139, selected time profile | Arbitrary external time sources and time-server administration denied. |
| F14-05 / authenticated senders | Collector .140, approved ingestion profile | No collector configuration, cross-tenant search or unrestricted reverse collection. |
| F14-06 / eligible bootstrap clients | Repository .141, approved retrieval profile | No repository publication or unrestricted Internet retrieval. |
| F14-07 / protection executor | Named platform capture API and separate data-mover path | Guest does not inherit API or repository-deletion rights. |
| F14-08 / storage or workload key client | KEY-REF, only the actual selected key-use role | No implicit guest KMS route; key administration and destruction separately controlled. |
| F14-09 / any base-fixture tenant | No public ingress or general Internet egress | Public PAZ and partner connectivity require a separately qualified service extension. |

Related documents: [SVC — Service, key and backup paths](../../architecture/shared-services/README.md#V14_SVC_START)  \|  [RA — Storage and security boundaries](../../architecture/reference/README.md#V14_RA_START)

[Previous chapter](6-worked-forwarding-and-return-route-schedule.md) · [Chapter index](README.md) · [Next chapter](8-mapping-the-schedules-into-each-vendor-stack.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0027 — Separate virtual-disk, guest-data, replication and administration paths](../../adr/0027-separate-virtual-disk-guest-data-replication-and-administration-paths.md)
- [ADR-0035 — Make shared-service replies select the originating security context](../../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<!-- END GENERATED DECISION LINKS -->
