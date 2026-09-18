# 3. Observe network paths and boundary enforcement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<a id="QCP_03"></a>

These four cards are controlled observations against the approved fixture. Bind native resource identities and actual configuration before execution.

Design basis and related records: [NBD §2](../../engineering/network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md#NBD_02)  •  [NBD §3](../../engineering/network-boundaries/3-make-service-replies-choose-the-originating-context.md#NBD_03)  •  [NET §3](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)


<a id="source-table-41"></a>

| Card / existing tests | Procedure and healthy control | Expected result / required artifact |
| --- | --- | --- |
| Q11-01: approved path and reply<br>CT-003, CT-007, CT-024 | Verify both endpoints; exercise F14-01. Locate the effective forward and reply path at native gateways and EC-01. Try a separately scoped reverse initiation. | Declared TCP/443 operation and reply work; unapproved new reverse initiation is denied. Retain path/rule/session evidence, not only an application success. |
| Q11-02: tenant isolation<br>CT-001, CT-002 | Prove each tenant’s local approved service. Observe bounded disallowed cross-tenant attempts in both directions and each offered family. | No unauthorized communication. Record endpoints, intended control, actual routing/policy and attributable denials. Unhealthy controls block the result. |
| Q11-03: same-domain policy<br>CT-021, CT-022 | Place the temporary probe in one approved domain; verify same-host/cross-host cases where applicable. Compare approved and unapproved communication. | Mandatory policy applies without requiring a physical gateway hop. Retain placement and enforcement evidence and the probe cleanup receipt. |
| Q11-04: shared-service return<br>CT-008, CT-023, CT-024 | Exercise the same resolver from both tenants. Trace each reply through its own SE/EC chain; check unbound service/admin targets and alternative connected paths. | Only entitled service use and origin-specific replies succeed. Retain service-side and edge observations; a shared endpoint is not tenant transit. |

Inspect both configured and effective forwarding. A flow seen at the intended ZIP proves that flow’s observation point; it does not alone eliminate another native path. Include connected routes, summaries, alternate interfaces, NAT/PBR and failure next hops that could change enforcement.

Every card records separate security and service outcomes. Unauthorized reachability fails the security assertion. An allowed connection that cannot operate fails its service assertion or is blocked by failed preconditions. Neither result is rescued by a successful Terraform run.

Continue with: [QCP §6](6-build-an-evidence-packet-a-reviewer-can-challenge.md#QCP_06)  •  [IT §4](../../templates/implementation-mop/4-test-procedure-and-actual-execution-record.md#IT_04)

[Previous chapter](2-size-and-control-the-qualification-fixture.md) · [Chapter index](README.md) · [Next chapter](4-observe-identity-storage-and-protocol-completeness.md)
