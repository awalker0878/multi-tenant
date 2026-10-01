# Platform capability and implementation review — 1 October 2026

Reviewed `implementation/all-waves` from `9d4c6685b6fd0fcb6df211aebd47857562265456`.
Code increments `b993470` and `249d75f` repair discovery and profile validation;
this alignment includes the catalog correction and regenerated examples. The
[existing B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md)
is the only delivery backlog. No deployed vendor environment was contacted.

## Findings implemented

| Finding | Correction and implementation owner | Evidence boundary |
|---|---|---|
| OpenStack dropped embedded allocation facts already available through its selected API. | `discovery/adapters/openstack.py` retains strict vCPU, RAM, nominal root/ephemeral/swap allocations; the existing normalizer consumes CPU/memory. | Missing facts remain unknown; no extra flavor lookup, endpoint or privilege. Nominal disk allocation is not total observed storage. |
| Native image/volume relations and deletion flags were lost. | The same owner retains bounded image/volume/attachment UUIDs, native booleans and optional guest device labels. | No guessed boot disk/order, path authority, complete consistency group, writer fence or deletion grant. |
| Catalog field validation was incomplete and duplicated. | `provisioner/profiles/requirements.py` now owns closed required fields and strict types/bounds for all ten families. Loader uses that owner. | Representation bounds are not product maxima. Unknown keys, coercions, missing required fields and malformed sets fail before resolution. |
| Standalone profile validation differed from full pipeline assurance recovery, and workload-count obligations were not enforced. | `profiles.validation` now owns assurance recovery, availability workload counts and recovery composition. Removed the redundant semantic branch, unused constant and parallel field table. | Full pipeline assurance recovery already existed; it was consolidated, not newly invented. Unsupported independent-site recovery remains refused. |
| Availability descriptions confused security zones with failure domains. | Catalog 18, high/maximum profile revision 2, corrected descriptions and regenerated five-request/three-platform examples. | No behavior, HA qualification, public exposure or deferred feature is enabled by a label or fixture. |

OpenStack collector admission is now `openstack-project-https-2`. Selector 1 is
retired without an alias. Re-enroll, issue matching independent campaign/witness/
credential material, capture new signed evidence and reassess. Retain old signed
records as history; never restamp their facts or reinterpret approved plans.

## Primary-source verification

Sources below were rechecked on 1 October 2026. Public API documentation supports
semantics, not installed API support, entitlement, visibility or native qualification.
A `latest` page may describe development code; clients keep deliberately pinned
contracts rather than adopting that page's release label automatically.

| Source | Verified distinction | Repository consequence / remaining evidence |
|---|---|---|
| [Nova Compute API](https://docs.openstack.org/api-ref/compute/) and [microversion history](https://docs.openstack.org/nova/latest/reference/api-microversion-history.html) | Embedded allocation details are available from microversion 2.47; RAM/swap and disk/ephemeral quantities have different units. The collector remains pinned to 2.79. | Typed conversion and unknown-field tests; no use of mutable flavor lookup or nominal disk size as a complete storage observation. |
| [Cinder API v3](https://docs.openstack.org/api-ref/block-storage/v3/) | Volume details expose attachment, server and volume references; encryption/multiattach and device labels have distinct meanings. | Whitelisted bounded relations, exact enclosing-volume checks and secret exclusion. Complete disk/guest/shared-writer evidence remains B16/B25/B38 work. |
| [Nova server groups](https://docs.openstack.org/nova/latest/user/server-groups.html) | Hard/soft affinity policies differ; server grouping alone is not an HA guarantee. | Security zones cannot stand in for observed failure topology. Qualify selected placement, reservation and recovery behavior separately. |
| [vSphere ClusterDasConfigInfo](https://developer.broadcom.com/xapis/vsphere-web-services-api/latest/vim.cluster.DasConfigInfo.html) | HA enablement, host monitoring and admission control are separate properties; disabled admission control does not assure restart capacity. | Do not infer native HA from a profile name or zone count. Exact cluster/per-VM policy, capacity and failure campaign remain required. |
| [Nutanix VMM v4.0 VM SDK](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.api.vm_api.html) | VM reads and operation APIs belong to explicit versioned native contracts, not a generic all-platform promise. | Existing AHV selector remains pinned. No new FNS/FVN/Move equivalence, credential privilege or directed migration route is inferred from the VM API. |

The [earlier semantic research](platform-migration-research.md) remains a dated
record for firewall rule models, SR-IOV bypass, DPDK, QoS minima/ceilings, encryption
layers, Move and native relocation. Its historical unfinished-work statements are
superseded by the current execution plan, not silently converted into new evidence.

## Coverage still open

The existing 97-capability vocabulary and 28 typed properties provide explicit
representation, not exhaustive implementation or native support. Profile requirements
are workload-specific; requiring every vendor feature on every workload would be an
incorrect interpretation of completeness. Keep explicit unknown, unsupported,
deferred, implemented and qualified states separate.

B05 retains actively used runtime owners and execution/state conversion. B14–B16
retain complete hardware/Glance/driver/key/service visibility and independent coverage
qualification. B17/B20 retain verified external dependencies, guided authoring and
owner-facing signing. B21 adoption is not an ownership-transfer workflow. B22 retains
durable fleet scheduling, global budgets, periodic monitoring/alerts, resumability
and measured estate qualification despite implemented batch/freshness/history paths.

B23–B29 still need the full admitted native reserve/prepare/plan/approve/apply/observe/
power/guest/service/activate chain. Transfer workers need independent target/root and
mTLS identity bindings, native writer exclusion and qualified credentials. Fencing,
final synchronization, traffic cutover, post-write recovery, whole-VM conversion and
all advertised directed routes remain implementation/qualification work. B44–B50
retain deployed HA/DR, security, retained-state conversion, pilot and operating release.
No new native or operational acceptance is recorded.

## Verification and source integrity

Targeted discovery, strict-profile and golden replay regressions exercise positive
and adversarial paths with synthetic evidence and loopback TLS. Local passes do not
replace final-revision CI, engine execution, real database-role tests, installed-wheel
checks or native campaigns. Store final test outcomes with the delivery revision;
failures and skipped environmental checks must remain visible.
Frozen source transcriptions, original signed records and Git history are retained.
Current design records consolidate chronological appendices without creating a second
roadmap. Actual active owners and independent safety controls are not deletion targets.
