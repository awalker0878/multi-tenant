# Appendix A — Canonical Object Model

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
## A.1 Workload Security Domain Schema — Illustrative


<a id="source-table-412"></a>

| WorkloadSecurityDomain:<br>  metadata:<br>    tenant\_id: string<br>    name: string<br>    owner: string<br>    lifecycle\_state: requested\|active\|restricted\|retiring\|retired<br>  security:<br>    profile: string<br>    assurance: standard\|enhanced\|dedicated<br>  placement:<br>    platform: auto\|&lt;profile&gt;<br>    site\_policy: string<br>    availability: string<br>    sovereignty: string<br>  zones:<br>    &lt;zone-class&gt;:<br>      enabled: bool<br>      dedicated\_domain: bool<br>  networks:<br>    &lt;network-name&gt;:<br>      zone: &lt;zone-class&gt;<br>      ipv4\_prefix\_size: int<br>      ipv6: bool<br>  services:<br>    &lt;service-name&gt;: enabled\|disabled\|profile<br>  flows:<br>    - source: identity<br>      destination: identity<br>      service: service-profile<br>      justification: string<br>  exposure:<br>    public\_ingress: false\|profile<br>    internet\_egress: false\|profile<br>    enterprise: false\|profile<br>  evidence\_profile: string<br> |
| --- |

## A.2 Security Domain Instance Schema — Illustrative


<a id="source-table-414"></a>

| SecurityDomainInstance:<br>  id: string<br>  zone\_class: PAZ\|OZ\|RZ\|HRZ\|REZ\|MZ<br>  tenant\_scope: string<br>  site: string<br>  platform\_profile: string<br>  assurance\_profile: string<br>  address\_scope\_id: string<br>  route\_policy\_id: generated<br>  edge\_attachment\_id: generated<br>  lifecycle\_state: active\|restricted\|retiring\|retired<br> |
| --- |

## A.3 Service Binding Schema — Illustrative


<a id="source-table-416"></a>

| ServiceBinding:<br>  id: string<br>  service\_profile: string<br>  consumer\_security\_domain: string<br>  endpoint\_profile: string<br>  direction: consumer\_to\_service\|service\_to\_consumer\|bidirectional<br>  policy: generated<br>  logging\_profile: string<br>  availability\_profile: string<br>  evidence\_required: true<br> |
| --- |

[Previous chapter](52-architecture-acceptance-criteria.md) · [Chapter index](README.md) · [Next chapter](62-appendix-b-terraform-root-and-module-patterns.md)
