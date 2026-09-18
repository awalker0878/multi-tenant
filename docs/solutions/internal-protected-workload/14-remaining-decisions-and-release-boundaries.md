# 14. Remaining decisions and release boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S14"></a>

This book resolves the missing worked connection between the guides and clarifies the acceptance dependency. It does not select a user's actual switch models, rack counts, firewall platform, installed versions, licensing, site addresses, service targets or cryptographic configuration. Those are actual implementation decisions, not documentation defects that can be closed by making up values.

Before commissioning this particular reference realization, the responsible owners must accept the native gateway/handoff mechanism, EC/SE context implementation, service-side return routing, supported protocol families, provider policy authority, co-residency, actual capacity and independent protection/trust dependencies. A product limitation may require a different qualified realization; record the variation at the parent architecture boundary.

The v1.4 change register distinguishes documentation addressed, proposed reference choice, site decision open, implementation not delivered, and verification not run. A statement that the documentation treatment exists is not a statement that the architecture has been deployed or authorized.


<a id="source-table-145"></a>

| Open decision | Record to complete | Blocking point |
| --- | --- | --- |
| Native domain and service handoff support | Exact component/API/provider/installer tuple, enabled features and actual context/interface mapping. | Platform/service qualification. |
| Service frontends and return routing | Supported endpoint routing, tenant authorization, management segregation and failure behavior. | Shared-service acceptance and dependent activation. |
| Offered families and protocol profiles | Actual addresses, source/target identities, local controls, crypto and service configuration. | Advertising the service class. |
| Co-residency and physical failure scope | Actual hosts, controllers, media, racks, edge and trust dependencies with approved sharing. | Relevant design and capacity acceptance. |
| Production readiness | Named owners, promised restore/recovery evidence, support, incident paths and valid authorization. | Production G3; never deferred by calling it later G4 work. |
| Live results | Actual observations for every applicable assertion and retained CT procedure. | Qualification or service acceptance, according to scope. |

Related documents: [GM — Gap progress and actual site decisions](../../assurance/gap-map/README.md#V14_GM_START)  \|  [QUAL — Acceptance requirements](../../assurance/site-qualification/README.md#V14_QUAL_START)

[Previous chapter](13-verification-assertions-and-actual-evidence.md) · [Chapter index](README.md) · [Next chapter](15-references-and-source-status.md)
