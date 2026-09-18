# 5. Dedicated handoff inventory and route ownership

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S05"></a>

The illustrative IPv6 handoffs are A01O = 2001:db8:200:1::/64, A01R = :2::/64, A02O = :3::/64, A02R = :4::/64, SH-01 = :5::/64 and SH-02 = :6::/64, all under 2001:db8:200::. On A links, the EC address is ::1 and native gateway is ::2; on SH links, EC is ::1 and SE is ::2. Use the full prefixes in the accompanying IPv6 schedule; the abbreviated notation in this paragraph is explanatory only. These link sizes and addresses require actual platform support before implementation.

The complete illustrated network has four tenant domain attachments A01O, A01R, A02O and A02R; two dedicated service-facing transit handoffs SH-01 and SH-02; and the service-side connections of SE-01 and SE-02. These are different accounting units. Physical redundant members, management interfaces and provider storage/protection paths are additional resources.

All link endpoint values below are illustrative interface identities. EC is the security edge and NG is the native domain gateway. The /30 link choices are an explanatory IPv4 example, not a statement that every product accepts the same subnet size or static-route configuration.

The tenant domain gateway is allowed to route its own networks locally. Routes to its other approved tenant zone and approved service endpoints point only at EC. EC knows only its own tenant prefixes and permitted service destinations. SE knows only the corresponding tenant return prefixes and the provider service network. No ordinary default route is required by this example. A supported default-route alternative must have equally constrained effective policy and no more-specific bypass.


<a id="source-table-66"></a>

| Handoff | Illustrative endpoint addresses | Routing and security scope |
| --- | --- | --- |
| A01O | 198.51.100.0/30: EC-01 .1; NG-D01O .2 | D01O to EC-01, independent of other domains. |
| A01R | 198.51.100.4/30: EC-01 .5; NG-D01R .6 | D01R to EC-01; Z01 policy separates OZ and RZ. |
| A02O | 198.51.100.8/30: EC-02 .9; NG-D02O .10 | D02O to EC-02; no tenant-01 membership. |
| A02R | 198.51.100.12/30: EC-02 .13; NG-D02R .14 | D02R to EC-02; Z02 policy separates OZ and RZ. |
| SH-01 | 198.51.100.16/30: EC-01 .17; SE-01 .18 | Only tenant-01 approved service flows. |
| SH-02 | 198.51.100.20/30: EC-02 .21; SE-02 .22 | Only tenant-02 approved service flows. |
| Service-side interfaces | SE-01 203.0.113.129; SE-02 203.0.113.130 | Provider-controlled SVC-REF; no native tenant gateway shares this segment. |

Related documents: [NET — Attachment accounting and bypass analysis](../../engineering/fabric/README.md#V14_NET_START)

[Previous chapter](4-tenant-attachment-and-address-schedule.md) · [Chapter index](README.md) · [Next chapter](6-worked-forwarding-and-return-route-schedule.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0007 — Allocate isolated domain attachments and qualify sharing](../../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)
- [ADR-0035 — Make shared-service replies select the originating security context](../../adr/0035-make-shared-service-replies-select-the-originating-security-context.md)

<!-- END GENERATED DECISION LINKS -->
