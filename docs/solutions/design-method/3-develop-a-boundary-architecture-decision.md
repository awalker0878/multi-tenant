# 3. Develop a boundary architecture decision

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx) · [Chapter index](README.md)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->
<a id="SDP_03"></a>

Use an explicit option record when choosing where inter-domain enforcement occurs. This worked decision is proposed, not accepted.

Design basis and related records: [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §29](../../architecture/reference/29-architecture-decisions-and-alternatives.md#RA_s_029)  •  [AT §6](../../templates/hld/6-architecture-decision-record.md#AT_06)

Decision DEV-ADR-01 concerns OZ-to-RZ communication for the common internal fixture. The required outcome is an attributable, jointly governed trust transition with controlled forward and reply paths, required inspection and safe failure behaviour. One useful criterion is whether another team can identify every enforcement function and every route that could avoid it.


<a id="source-table-40"></a>

| Option | Architectural benefit | Conditions and cost of acceptance |
| --- | --- | --- |
| Provider routed security edge | One explicit boundary service separates vendor-native domain routing from approved trust transitions. | Requires isolated attachments, sufficient inspection/session capacity and no connected-route or return-path bypass. |
| Qualified native or distributed boundary | May avoid additional centralized hops for some paths. | Must locate all required ZIP functions, protect provider authority and prove same-host, failure and inspection behaviour. A distributed firewall alone is not the complete argument. |
| Common unrestricted transit | Simple connectivity and fewer visible contexts. | Rejected for the base service: it introduces reachability without the required boundary authority and can bypass downstream enforcement. |

Proposed disposition: retain the parent’s explicit edge pattern for the first qualification campaign. Evaluate a native/distributed alternative as a separately scoped variation only where it delivers the required functions. This is not a vendor ranking; the site’s supported release, traffic and assurance requirements determine feasibility.

Record consequences in the LLD: domain and edge context identities, service-facing attachments, permitted prefixes, return routing, policy ownership, failure load and qualification observations. Any new variation must also change the relevant build and test records; an ADR title alone does not change the architecture.

Continue with: [NBD §1](../../engineering/network-boundaries/1-count-and-assign-the-actual-isolation-units.md#NBD_01)  •  [NBD §2](../../engineering/network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md#NBD_02)  •  [QCP §3](../../assurance/qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md#QCP_03)

[Previous chapter](2-choose-sharing-at-each-infrastructure-layer.md) · [Chapter index](README.md) · [Next chapter](4-turn-dependencies-into-explicit-service-interfaces.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions](../../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)

<!-- END GENERATED DECISION LINKS -->
